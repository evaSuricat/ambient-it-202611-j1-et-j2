# E20 · La version corrigée, à lire

Ce dossier contient la réponse à l'exercice. **Ouvrez-le après l'étape 4**, pas avant : chercher les trois fuites soi-même est le but de l'exercice.

Vous n'avez rien à lancer et rien à installer. Tout se lit.

## Les trois fichiers

| Fichier | Ce que c'est |
|---|---|
| `Dockerfile.corrige` | La recette de l'image, réécrite sans fuite |
| `.dockerignore` | La liste de ce qui ne doit jamais partir dans une image |
| `historique-corrige.txt` | Ce que l'image corrigée raconte d'elle-même : la sortie réelle de `docker history` |

## Avant, après : les trois fuites

| Fuite | Dans `depart/Dockerfile` | Dans `Dockerfile.corrige` |
|---|---|---|
| 1. Un secret écrit dans la recette | `ARG JETON_DEPLOIEMENT=jeton-…` et `ENV PIGALA_CLE=cle-…` : les deux valeurs restent lisibles dans l'image | Plus aucune ligne `ARG` ni `ENV`. Le jeton est prêté à l'image le temps d'une seule commande, par `RUN --mount=type=secret,id=jeton`, puis il repart |
| 2. Tout le dossier copié | `COPY . .` : les réservations des clients et le fichier de secrets partent dans l'image | `COPY app.py .` : un seul fichier, celui dont l'application a besoin |
| 3. Une suppression qui ne supprime rien | `rm secrets.env` : le fichier reste dans la couche d'avant | Plus de `rm`. Le fichier n'entre jamais dans l'image, il n'y a donc rien à supprimer |

## Le `.dockerignore`, ligne par ligne

Ce fichier se pose à côté du `Dockerfile`. Docker ignore tout ce qu'il liste, même si une ligne `COPY . .` revenait par erreur. C'est une ceinture en plus des bretelles.

| Ligne | Ce qu'elle écarte |
|---|---|
| `secrets.env` | Le fichier de secrets |
| `reservations.csv` | Les réservations des clients |
| `*.db` | Toute base de données |
| `donnees` | Le dossier des données |
| `.git` | L'historique du dépôt, qui peut contenir d'anciens secrets |
| `.venv` | L'environnement Python du poste |
| `jeton.txt` | Le fichier qui contient le jeton prêté pendant la construction |

## La preuve

Ouvrez `historique-corrige.txt` et comparez-le à `depart/historique-docker.txt`.

- Cherchez « factice » dans les deux fichiers (`Ctrl+F`).
- Dans `depart/historique-docker.txt` : trois lignes le contiennent.
- Dans `historique-corrige.txt` : aucune.

## Ce qui a été mesuré

Relevé du 17/11/2026 sur le poste de la formatrice, avec Docker 25.0.3 :

| Vérification | Résultat |
|---|---|
| L'image corrigée se construit | Oui |
| Le jeton ou la clé dans `docker history` | 0 ligne |
| Les variables d'environnement de l'image | Aucune clé, seulement le `PATH` habituel |
| Le contenu de `/app` | Deux fichiers : `app.py` et `verification.log` |
| `secrets.env`, `reservations.csv` ou `jeton.txt` dans les couches de l'image | 0 fichier |
| Le texte du jeton, de la clé, ou une adresse de courriel dans `/app` | 0 fichier |

## Ce que cette version ne fait pas

- Elle ne dit pas où ranger le vrai jeton. Sur un vrai projet, il vit dans un gestionnaire de secrets, pas dans un fichier du dépôt.
- Elle ne répare pas une image déjà publiée. Si une image avec un secret est partie, il faut changer le secret : supprimer l'image ne suffit pas.
