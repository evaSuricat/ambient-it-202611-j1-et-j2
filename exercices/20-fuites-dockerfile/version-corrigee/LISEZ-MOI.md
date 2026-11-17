# E20 · La version corrigée, à lire

Ce dossier contient la réponse à l'exercice. **Ouvrez-le après l'étape 4**, pas avant : chercher les trois fuites soi-même est le but de l'exercice.

Vous n'avez rien à lancer et rien à installer. Tout se lit.

## Les trois fichiers

| Fichier | Ce que c'est |
|---|---|
| `Dockerfile.corrige` | La recette de l'image, réécrite sans fuite |
| `.dockerignore` | La liste de ce qui ne doit jamais partir dans une image |
| `historique-corrige.txt` | Ce que l'image corrigée raconte d'elle-même : la sortie réelle de `docker history` |

## Ce que contient un fichier comme `secrets.env`

Dans l'exercice, `depart/secrets.env` contient une seule ligne, avec un faux jeton.

Dans un vrai projet, c'est le fichier où l'on range les valeurs qui donnent accès à quelque chose. Une ligne par valeur, sous la forme `NOM=valeur`. Le plus souvent :

| Ce qu'on y trouve | À quoi ça donne accès |
|---|---|
| Le mot de passe de la base de données | Toutes les données des clients, en lecture et en écriture |
| Une clé d'API d'un service payant (envoi de mails ou de SMS, paiement en ligne, cartes) | Le compte de l'entreprise chez ce prestataire, et sa facture |
| Une clé d'API d'un modèle d'IA | La consommation de tokens, facturée à l'entreprise |
| Un jeton de déploiement | Le droit de mettre en ligne une nouvelle version du site |
| Les identifiants du serveur de mail | Le droit d'envoyer des messages au nom de l'entreprise |
| La clé qui signe les sessions des utilisateurs | La possibilité de se faire passer pour n'importe quel utilisateur connecté |

Pour le Pigala, ce serait par exemple le mot de passe de la base des réservations, la clé du service qui envoie les SMS de confirmation, et le jeton qui publie le site.

**À retenir :** ce fichier ne contient pas des données, il contient des clés. Qui l'a n'a rien à pirater : il entre par la porte. C'est pour cela qu'il ne doit se trouver ni dans une image Docker, ni dans un dépôt Git, ni dans un prompt.

Le nom vient de l'habitude : `.env` pour « environnement ». On rencontre surtout le nom `.env` tout court.

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
