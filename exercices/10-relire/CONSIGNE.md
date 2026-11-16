# E10 · Relire ce qu'on n'a pas écrit

**Point du programme** : relecture et amélioration du code généré.

**Durée** : 15 minutes.

## Ce qu'on fait

`exercices/10-relire/depart/` contient la page complète avec sa carte. On la mesure, on la relit avec la grille de l'exercice 5, on corrige, on remesure.

0. **Le point de départ.** Tout le monde part des fichiers fournis dans `exercices/10-relire/depart/` : la page (`index.html`), sa feuille de style (`style.css`) et le dossier `css/`. Il n'y a rien à copier, et vous n'avez pas besoin de votre page du jour 1.

   Enregistrez ce point de départ, depuis la racine de votre dossier `stagiaire_J1_et_J2`, avant tout `cd`, une ligne après l'autre :

       git add exercices/10-relire
       git commit -m "E10 : état avant relecture"

   Résultat attendu : « nothing to commit » est normal si rien n'a changé depuis le clonage. Sinon, une ligne « files changed ».

1. **Le Lighthouse « avant », tant que rien n'est corrigé.** Lighthouse refuse une page ouverte par double-clic : il lui faut une adresse `http`. Ouvrez un deuxième terminal (bouton **+** du panneau Terminal), puis :

       cd exercices/10-relire/depart
       python -m http.server 8000 --bind 127.0.0.1

   `http.server` sert ce dossier sur votre machine seulement. Si `python` n'existe pas (Mac, certains Linux), tapez `python3`. Résultat attendu : `Serving HTTP on 127.0.0.1 port 8000`, et le terminal reste en attente, gardez-le ouvert. Si le pare-feu Windows pose une question, répondez Annuler.

   Dans Chrome, ouvrez http://127.0.0.1:8000/, puis F12, onglet **Lighthouse** (derrière `>>` s'il n'est pas visible). Device : **Desktop**. Categories : **Accessibility** et **Best practices** seulement. **Analyze page load**. Créez `exercices/10-relire/depart/lighthouse.md` et notez-y les deux scores.

   Si tout s'affiche en « Error », avec `chrome-error` dans l'adresse du rapport : Chrome n'a pas chargé la page, ce n'est pas votre code. Une extension peut en être la cause. Recommencez dans une fenêtre de navigation privée (Ctrl+Maj+N).

2. **La relecture dans Claude Code.** La commande `/verifier-page` vient de l'exercice 5 : c'est le skill `.claude/skills/verifier-page/SKILL.md`, à la racine de votre dossier, lu par Claude Code et par Copilot. Si vous ne l'avez pas, copiez le dossier `ressources/skills/verifier-page` dans `.claude/skills/` à la racine (créez `.claude/skills/` s'il n'existe pas : clic droit dans l'explorateur, « New Folder »). Nouvelle conversation, puis :

       /verifier-page exercices/10-relire/depart/index.html exercices/10-relire/depart/style.css

3. **La même relecture dans Copilot Chat.** New Chat, sélecteur sur Agent, retirez la pastille de fichier si elle est là, puis `/verifier-page` suivi des deux mêmes chemins. Comparez les deux rapports. Si « Run in terminal? » apparaît, lisez la commande : des calculs et des `print`, aucun fichier.

4. **Appliquer au moins deux corrections** de la liste « À corriger », à la main ou en demandant à l'outil. Nommez les points, pas les numéros, car la numérotation change d'un rapport à l'autre : « Dans exercices/10-relire/depart/, applique les corrections de ton rapport sur … ». Laissez de côté ce qui est une décision à prendre ou une précaution pour plus tard.

   Prenez les remarques de votre rapport, et regardez la page vous-même : un outil ne voit pas tout.

   Sur la page fournie, Lighthouse signale une seule chose, dans Best practices : « Browser errors were logged to the console », avec une erreur 404 sur `favicon.ico`. Chrome demande ce fichier tout seul, pour l'icône de l'onglet, et la page n'en déclare pas. Correction en une ligne, dans le `<head>` de `index.html` : `<link rel="icon" href="data:,">`, qui déclare une icône vide. Le score passe de 96 à 100 (relevé le 17/11/2026). C'est une rustine : le brief ne fournit aucun logo, la vraie icône est à demander au client.

5. **Le Lighthouse « après ».** Rechargez la page (F5), onglet Lighthouse, **+** pour un nouveau rapport, **Analyze page load**. Notez les deux scores dans `lighthouse.md`. Puis arrêtez le serveur : Ctrl+C dans son terminal.

6. **Committer**, depuis la racine, en nommant vos corrections dans le message :

       git add exercices/10-relire
       git commit -m "E10 : corrections de la relecture, Lighthouse avant et après"

   Résultat attendu : une ligne « 2 files changed » ou plus.

## Livrable

Deux corrections commitées, `exercices/10-relire/depart/lighthouse.md` avec les scores avant et après.

## Ce qu'on retient

Lighthouse tourne dans Chrome, hors ligne. Il ne voit pas tout : le contraste, oui ; un texte alternatif faux, non ; un ordre de titres cassé, en partie ; un plat inventé, jamais. Un 100 ne veut pas dire que la page est bonne, et un score qui ne bouge pas ne veut pas dire que la correction est inutile. La grille et l'œil complètent l'outil.
