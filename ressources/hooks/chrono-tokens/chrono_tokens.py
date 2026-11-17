# -*- coding: utf-8 -*-
"""Chronomètre et compteur de tokens par prompt.

Appelé par deux hooks Claude Code déclarés dans .claude/settings.local.json :
  chrono_tokens.py debut   (hook UserPromptSubmit, à l'envoi d'un prompt)
  chrono_tokens.py fin     (hook Stop, quand Claude a fini de répondre)

Règles de sûreté :
  - rien n'est écrit sur la sortie standard (elle serait injectée dans le contexte
    du modèle par UserPromptSubmit) ni sur la sortie d'erreur ;
  - le code de sortie est toujours 0 ; toute erreur interne est consignée dans
    erreurs.log, à côté de ce script ;
  - le script retrouve son dossier tout seul (emplacement du fichier), sans
    variable d'environnement ni dossier temporaire.

Bibliothèque standard uniquement.
"""

import json
import os
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
ETAT = DOSSIER / "etat.json"
JOURNAL = DOSSIER / "journal.md"
ERREURS = DOSSIER / "erreurs.log"

# Prix par million de tokens, en dollars, relevés dans la documentation Anthropic
# embarquée le 12/11/2026. À mettre à jour si les tarifs changent.
PRIX_DATE = "12/11/2026"
PRIX = {
    "claude-fable-5-2": {"entree": 8.0, "sortie": 40.0, "ecr5": 10.0, "ecr1h": 16.0, "lecture": 0.20},
    # Fable 5.1 : 10 et 50 $, lecture 0,25 $ (doc embarquée) ; écritures déduites
    # de la règle générale (1,25 fois l'entrée en 5 min, 2 fois en 1 h).
    "claude-fable-5-1": {"entree": 10.0, "sortie": 50.0, "ecr5": 12.5, "ecr1h": 20.0, "lecture": 0.25},
    "claude-opus-5-5": {"entree": 4.0, "sortie": 20.0, "ecr5": 5.0, "ecr1h": 8.0, "lecture": 0.20},
    "claude-sonnet-5-5": {"entree": 2.0, "sortie": 10.0, "ecr5": 2.5, "ecr1h": 4.0, "lecture": 0.10},
    "claude-haiku-5-5": {"entree": 0.10, "sortie": 0.50, "ecr5": 0.125, "ecr1h": 0.20, "lecture": 0.01},
}

# VS Code ajoute devant le prompt le fichier ouvert ou les lignes sélectionnées, entre balises <ide_...>.
# On les retire du texte affiché dans le journal : elles contiennent un chemin du disque, pas le prompt.
REGEX_IDE = re.compile(r"<(ide_[a-z_]+)>.*?</\1>", re.DOTALL)
REGEX_EXERCICE = re.compile(r"exercices[/\\](\d\d-[a-z0-9-]+|bonus-[a-z-]+)", re.IGNORECASE)
HORS_EXERCICE = "hors exercice"

EN_TETE = [
    "# Journal : durée et tokens par prompt",
    "",
    "- Ce journal mesure, pour chaque prompt envoyé, la durée de la réponse et les tokens consommés par Claude (colonnes sous-agents à part), relevés dans le transcript de la session.",
    f"- Le coût est un équivalent API (tarifs du {PRIX_DATE}, par modèle) : au forfait, rien n'est facturé ; si le transcript ne ventile pas l'écriture de cache entre 5 min et 1 h, elle est comptée au tarif 5 min.",
    "- Limites : un prompt interrompu avant la fin n'a pas de ligne, un modèle inconnu du tableau de prix laisse le coût vide, et le transcript peut avoir un léger retard à la fin de la réponse.",
    "",
    "| Date | Exercice | Début | Fin | Durée (min:s) | Modèle | Entrée | Sortie | Écriture cache | Lecture cache | Coût équivalent API ($) | Tokens sous-agents | Dont sous-agents ($) | Début du prompt |",
    "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
]


# ----------------------------------------------------------------- utilitaires

def maintenant():
    return datetime.now().astimezone()


def consigner_erreur(message):
    try:
        with open(ERREURS, "a", encoding="utf-8", newline="\n") as f:
            f.write(f"{maintenant().isoformat(timespec='seconds')} {message}\n")
    except Exception:
        pass


def ecrire_atomique(chemin, texte):
    tmp = chemin.with_name(chemin.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(texte)
    os.replace(tmp, chemin)


def lire_etat():
    vide = {"sessions": {}, "lignes": []}
    if not ETAT.exists():
        return vide
    try:
        with open(ETAT, "r", encoding="utf-8") as f:
            etat = json.load(f)
        etat.setdefault("sessions", {})
        etat.setdefault("lignes", [])
        return etat
    except Exception as e:
        consigner_erreur(f"etat.json illisible, remis à zéro : {e!r}")
        return vide


def lire_entree():
    brut = sys.stdin.buffer.read()
    if brut[:2] in (b"\xff\xfe", b"\xfe\xff"):
        texte = brut.decode("utf-16")
    else:
        texte = brut.decode("utf-8-sig", errors="replace")
    return json.loads(texte)


def compter_lignes(chemin):
    n = 0
    with open(chemin, "rb") as f:
        for _ in f:
            n += 1
    return n


def chemin_transcript(donnees):
    brut = donnees.get("transcript_path") or ""
    return Path(os.path.expanduser(brut)) if brut else None


def dossier_sous_agents(transcript):
    """Les sous-agents ont leur propre transcript dans <session>/subagents/agent-*.jsonl."""
    s = str(transcript)
    if not s.lower().endswith(".jsonl"):
        return None
    return Path(s[:-6]) / "subagents"


def lister_sous_agents(transcript):
    dossier = dossier_sous_agents(transcript)
    resultat = {}
    if dossier and dossier.is_dir():
        for fichier in sorted(dossier.glob("*.jsonl")):
            try:
                resultat[fichier.name] = compter_lignes(fichier)
            except Exception as e:
                consigner_erreur(f"sous-agent illisible {fichier.name} : {e!r}")
    return resultat


# ------------------------------------------------------------------ tokens/coût

def lire_usage(chemin, depart, prefixe=""):
    """Lit un transcript JSONL à partir de la ligne `depart` (0 = début).

    Retourne ({id: (modèle, usage)}, nombre de lignes lues). Un même message
    de l'assistant peut figurer sur plusieurs lignes avec le même message.id :
    on ne garde qu'une entrée par id, celle dont output_tokens est le plus grand.
    """
    messages = {}
    nlignes = 0
    with open(chemin, "r", encoding="utf-8", errors="replace") as f:
        for i, ligne in enumerate(f):
            nlignes = i + 1
            if i < depart:
                continue
            try:
                d = json.loads(ligne)
            except ValueError:
                continue  # ligne en cours d'écriture
            if not isinstance(d, dict) or d.get("type") != "assistant":
                continue
            m = d.get("message")
            if not isinstance(m, dict):
                continue
            usage = m.get("usage")
            modele = m.get("model")
            if not isinstance(usage, dict) or not modele or modele == "<synthetic>":
                continue
            cle = prefixe + str(m.get("id") or d.get("uuid") or f"ligne{i}")
            sortie = usage.get("output_tokens") or 0
            ancien = messages.get(cle)
            if ancien is None or sortie >= (ancien[1].get("output_tokens") or 0):
                messages[cle] = (modele, usage)
    return messages, nlignes


def agreger(messages, cumul=None):
    """Additionne l'usage par modèle."""
    cumul = cumul if cumul is not None else {}
    for modele, usage in messages.values():
        t = cumul.setdefault(modele, {"entree": 0, "sortie": 0, "ecr": 0, "ecr5": 0, "ecr1h": 0, "lecture": 0})
        ecr = usage.get("cache_creation_input_tokens") or 0
        detail = usage.get("cache_creation")
        t["entree"] += usage.get("input_tokens") or 0
        t["sortie"] += usage.get("output_tokens") or 0
        t["lecture"] += usage.get("cache_read_input_tokens") or 0
        t["ecr"] += ecr
        if isinstance(detail, dict) and ("ephemeral_5m_input_tokens" in detail or "ephemeral_1h_input_tokens" in detail):
            t["ecr5"] += detail.get("ephemeral_5m_input_tokens") or 0
            t["ecr1h"] += detail.get("ephemeral_1h_input_tokens") or 0
        else:
            t["ecr5"] += ecr  # pas de ventilation : tarif 5 min
    return cumul


def prix_du_modele(modele):
    if modele in PRIX:
        return PRIX[modele]
    for nom, prix in PRIX.items():
        if modele.startswith(nom + "-"):  # par exemple un suffixe de date
            return prix
    return None


def cout(cumul):
    """Coût en dollars, ou None si un modèle est inconnu."""
    total = 0.0
    for modele, t in cumul.items():
        p = prix_du_modele(modele)
        if p is None:
            return None
        total += (
            t["entree"] * p["entree"]
            + t["sortie"] * p["sortie"]
            + t["ecr5"] * p["ecr5"]
            + t["ecr1h"] * p["ecr1h"]
            + t["lecture"] * p["lecture"]
        ) / 1_000_000
    return total


def somme(cumul, champ):
    return sum(t[champ] for t in cumul.values())


# ---------------------------------------------------------------------- journal

def cellule(texte):
    return str(texte).replace("|", "\\|").replace("\n", " ")


def format_cout(valeur):
    return "" if valeur is None else f"{valeur:.4f}".replace(".", ",")


def format_duree(secondes):
    secondes = max(0, int(round(secondes)))
    return f"{secondes // 60}:{secondes % 60:02d}"


def rendre_journal(lignes):
    sortie = list(EN_TETE)
    for r in sorted(lignes, key=lambda x: x.get("debut_iso", "")):
        sortie.append(
            "| " + " | ".join(
                cellule(c) for c in (
                    r.get("date", ""), r.get("exercice", ""), r.get("debut", ""), r.get("fin", ""),
                    format_duree(r.get("duree_s", 0)), r.get("modeles", ""),
                    r.get("entree", 0), r.get("sortie", 0), r.get("ecriture", 0), r.get("lecture", 0),
                    format_cout(r.get("cout")), r.get("sa_tokens", "") or "", format_cout(r.get("sa_cout")) if r.get("sa_tokens") else "",
                    r.get("prompt", ""),
                )
            ) + " |"
        )
    return "\n".join(sortie) + "\n"


# ------------------------------------------------------------------- les hooks

def debut(donnees):
    sid = donnees.get("session_id") or "inconnue"
    prompt = " ".join(REGEX_IDE.sub(" ", str(donnees.get("prompt") or "")).split())
    m = REGEX_EXERCICE.search(str(donnees.get("prompt") or ""))
    exercice = m.group(1).lower() if m else HORS_EXERCICE
    transcript = chemin_transcript(donnees)
    n = 0
    sous = {}
    if transcript is not None:
        if transcript.exists():
            n = compter_lignes(transcript)
        sous = lister_sous_agents(transcript)
    t0 = maintenant()
    etat = lire_etat()
    etat["sessions"][sid] = {
        "debut_iso": t0.isoformat(timespec="seconds"),
        "exercice": exercice,
        "prompt": prompt[:80],
        "lignes_debut": n,
        "sous_agents": sous,
        "transcript_path": str(transcript) if transcript else "",
    }
    ecrire_atomique(ETAT, json.dumps(etat, ensure_ascii=False, indent=2) + "\n")


def lire_stabilise(chemin, depart, prefixe=""):
    """Le transcript peut avoir un léger retard à l'arrêt : on relit jusqu'à ce que
    le nombre de lignes ne bouge plus (au plus 4 lectures, 0,6 s entre deux)."""
    precedent = None
    for _ in range(4):
        messages, n = lire_usage(chemin, depart, prefixe)
        if precedent is not None and n == precedent:
            break
        precedent = n
        time.sleep(0.6)
    return messages


def fin(donnees):
    sid = donnees.get("session_id") or "inconnue"
    etat = lire_etat()
    sess = etat["sessions"].get(sid)
    if not sess:
        raise ValueError(f"fin sans debut pour la session {sid}")
    transcript = chemin_transcript(donnees) or Path(sess.get("transcript_path") or "")
    if not transcript.is_file():
        raise FileNotFoundError(f"transcript introuvable : {transcript}")

    principal = agreger(lire_stabilise(transcript, int(sess.get("lignes_debut", 0))))

    sous_cumul = {}
    dossier = dossier_sous_agents(transcript)
    if dossier and dossier.is_dir():
        for fichier in sorted(dossier.glob("*.jsonl")):
            try:
                depart = int(sess.get("sous_agents", {}).get(fichier.name, 0))
                agreger(lire_stabilise(fichier, depart, prefixe=fichier.name + ":"), sous_cumul)
            except Exception as e:
                consigner_erreur(f"sous-agent ignoré {fichier.name} : {e!r}")

    t0 = datetime.fromisoformat(sess["debut_iso"])
    t1 = maintenant()
    c_princ = cout(principal)
    c_sous = cout(sous_cumul)
    sa_tokens = sum(somme(sous_cumul, c) for c in ("entree", "sortie", "ecr", "lecture"))
    total = None if (c_princ is None or c_sous is None) else c_princ + c_sous

    modeles = ", ".join(sorted(principal))
    if sous_cumul:
        modeles += (" ; " if modeles else "") + "sous-agents : " + ", ".join(sorted(sous_cumul))

    ligne = {
        "cle": sid + "|" + sess["debut_iso"],
        "debut_iso": sess["debut_iso"],
        "date": t0.strftime("%d/%m/%Y"),
        "exercice": sess["exercice"],
        "debut": t0.strftime("%H:%M:%S"),
        "fin": t1.strftime("%H:%M:%S"),
        "duree_s": (t1 - t0).total_seconds(),
        "modeles": modeles,
        "entree": somme(principal, "entree"),
        "sortie": somme(principal, "sortie"),
        "ecriture": somme(principal, "ecr"),
        "lecture": somme(principal, "lecture"),
        "cout": total,
        "sa_tokens": sa_tokens,
        "sa_cout": c_sous,
        "prompt": sess["prompt"],
    }
    # Un seul enregistrement par prompt : un second arrêt pour le même prompt remplace le premier.
    etat["lignes"] = [r for r in etat["lignes"] if r.get("cle") != ligne["cle"]] + [ligne]
    ecrire_atomique(ETAT, json.dumps(etat, ensure_ascii=False, indent=2) + "\n")
    ecrire_atomique(JOURNAL, rendre_journal(etat["lignes"]))


def main():
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")
    try:
        if len(sys.argv) != 2 or sys.argv[1] not in ("debut", "fin"):
            raise ValueError(f"argument attendu : debut ou fin, reçu {sys.argv[1:]}")
        donnees = lire_entree()
        if sys.argv[1] == "debut":
            debut(donnees)
        else:
            fin(donnees)
    except Exception as e:
        consigner_erreur(f"{sys.argv[1:]} : {e!r} | {traceback.format_exc().splitlines()[-3:]}")
    sys.exit(0)


if __name__ == "__main__":
    main()
