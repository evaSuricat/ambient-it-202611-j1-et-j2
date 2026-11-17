# Chrono et tokens : ce que coûte chaque prompt

Un hook pour Claude Code. Pour chaque prompt que vous envoyez, il note dans un journal : l'exercice, l'heure de début et de fin, la durée, le modèle, les tokens (entrée, sortie, écriture et lecture du cache, sous-agents à part) et le coût en équivalent API.

**Un hook** est un petit programme que Claude Code lance lui-même à un moment précis, sans passer par le modèle. Ici, deux moments : `UserPromptSubmit` (vous venez d'envoyer un prompt) et `Stop` (la réponse est finie). À ne pas confondre avec le hook **Git** du dossier voisin (`ressources/hooks/pre-commit`) : celui-là, c'est Git qui le lance, avant un commit.

Il est en réserve : rien ne s'installe tout seul. Il ne sert qu'avec Claude Code, pas avec Copilot.

## Ce qu'il écrit, et où

Tout reste sur votre poste, dans `.claude/chrono-tokens/` :

- `journal.md` : une ligne par prompt. La dernière colonne contient les 80 premiers caractères de votre prompt ;
- `etat.json` : son brouillon de travail ;
- `erreurs.log` : ses erreurs, s'il en a. Il n'empêche jamais un prompt de partir.

Le `.gitignore` du dépôt ignore déjà `.claude/chrono-tokens/` et `.claude/settings.local.json` : rien de tout cela ne part dans un commit.

## Installer

Depuis la racine de votre dossier `stagiaire_J1_et_J2`, dans un terminal de VS Code, une ligne après l'autre (elles marchent sous Windows comme sous Linux) :

```
mkdir .claude/chrono-tokens
cp ressources/hooks/chrono-tokens/chrono_tokens.py .claude/chrono-tokens/
cp ressources/hooks/chrono-tokens/settings.local.exemple.json .claude/settings.local.json
```

La première ligne crée le dossier du hook. La deuxième y copie le script. La troisième pose le réglage qui dit à Claude Code quand le lancer.

Résultat attendu : aucun message. Une erreur « No such file » (« Cannot find path » sous PowerShell) veut dire que vous n'êtes pas à la racine : rien n'a été écrit, vérifiez avec `pwd`.

**Attention à la troisième ligne** : si vous avez déjà un fichier `.claude/settings.local.json`, elle l'écrase. Dans ce cas, ne la lancez pas : ouvrez les deux fichiers et recopiez le bloc `"hooks"` de l'exemple dans le vôtre.

**Sous macOS ou Linux**, la commande `py` n'existe pas. Ouvrez `.claude/settings.local.json` et, aux deux endroits, remplacez `"command": "py"` par `"command": "python3"`, et retirez `"-3.12", ` au début de la liste `"args"`.

## Vérifier

1. Dans Claude Code, tapez `/hooks`. Résultat attendu : `UserPromptSubmit` et `Stop`, marqués « Local ». S'ils n'y sont pas, fermez la conversation et ouvrez-en une nouvelle.
2. Envoyez un prompt, attendez la fin de la réponse.
3. Ouvrez `.claude/chrono-tokens/journal.md` : une ligne est apparue.

Si rien n'apparaît, regardez `.claude/chrono-tokens/erreurs.log`.

## Retirer

Supprimez le dossier `.claude/chrono-tokens/` et le fichier `.claude/settings.local.json` (ou seulement son bloc `"hooks"` si vous y aviez d'autres réglages).

## Limites à connaître

- **Les tarifs sont écrits en dur** en tête du script, relevés le 12/11/2026. Lisez les coûts comme des ordres de grandeur, et mettez le tableau à jour avant de vous y fier. Un modèle absent du tableau laisse la colonne du coût vide.
- **Le coût est un équivalent API.** Avec un forfait, rien n'est facturé au prompt, mais les tokens comptent dans vos limites d'usage.
- Il mesure le temps de réponse de chaque prompt, pas le temps que vous passez sur l'exercice.
- Un prompt interrompu (Échap) n'a pas de ligne.
- L'exercice est déduit du chemin `exercices/NN-nom` cité dans le prompt. Sans chemin, la ligne est rangée « hors exercice ».
- Essayé sous Windows avec Python 3.12. La variante macOS et Linux n'a pas été essayée.
