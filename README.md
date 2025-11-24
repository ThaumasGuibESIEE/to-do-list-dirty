# to-do-list app
To-Do-List application built with django to Create, Update and Delete tasks.
<br>
<br>
![todolist](https://user-images.githubusercontent.com/65074901/125083144-a5e03900-e0e5-11eb-9092-da716a30a5f3.JPG)

## Versionning et commits
- Numérotation : suivre [SemVer](https://semver.org/lang/fr/) `MAJEUR.MINEUR.PATCH`. Exemple : `1.0.1` pour un correctif, `1.1.0` pour une nouvelle fonctionnalité compatible, `2.0.0` pour une rupture.
- Messages de commit : utiliser [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) (`type(scope): message`), par ex. `feat(tasks): add bulk edit` ou `fix(api): handle empty title`.
- Bump + tag + archive : exécuter `./scripts/build.sh version=X.Y.Z` (via Git Bash) depuis la racine pour mettre à jour `todo/settings.py`, créer un commit “Bump version to X.Y.Z”, taguer et générer `todolist-X.Y.Z.zip`.
