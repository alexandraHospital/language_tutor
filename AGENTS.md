# AGENTS.md

Instructions pour les agents de code travaillant dans ce dépôt.

## Vue d'ensemble du projet

- Projet : Language Tutor - a cli application to train speaking languages
- Stack : Python 3.12, Whisper
- Point d'entrée : `tutor.py`
- Tests : `pytest` (dossier `tests/`)

## Commandes

```bash
# Installer l'environnement
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Lancer les tests
pytest -q

# Vérifications qualité (obligatoires avant tout commit)
ruff check .
ruff format --check .
```

## Règles de code

- Python moderne : type hints partout, f-strings, `pathlib`, dataclasses/pydantic pour les modèles.
- Style : suivre `ruff format` (issu de Black). Pas de code mort, pas de commentaires qui paraphrasent le code.
- Fonctions courtes et pures quand c'est possible ; éviter les effets de bord cachés.
- Erreurs : lever des exceptions typées du projet, ne jamais avaler une exception silencieusement (`except: pass` interdit).
- Pas de secrets dans le code : lire la config depuis l'environnement / `.env` (voir `.env.example`).
- Écrire le nom des fonctions et les commentaires en anglais
- Compléter le readme avec la fonctionnalité codée.

## Tests

- Tout nouveau code s'accompagne de tests pytest (unitaires ; integration si pertinent).
- Nommer les tests `test_<comportement>_<condition>_<résultat_attendu>`.
- Utiliser des fixtures (`conftest.py`), éviter les mocks superflus ; mocker uniquement les frontières (réseau, DB, horloge).
- Avant de dire qu'une tâche est terminée : `pytest -q`, `ruff check .` et `ruff format --check .` passent sans erreur.

## Workflow Git

- Ne jamais commiter sans que ça ait été dit explicitement par `git commit`
- Ne jamais pusher sans que ça ait été dit explicitement par `git push`
- Commits courts et impératifs : `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, et une description courte de ce qui a été fait.
- Ne jamais committer directement sur `master` ; passer par une branche + PR.
- Le nom de la branche créée est court et est inspiré de la feature (par exemple `add_voice_in_response`)
- Ne pas toucher aux fichiers générés (`lock`, `dist/`, caches) sauf nécessité.

## Comportement attendu de l'agent

- Lire le code existant avant de modifier : respecter les conventions en place plutôt que d'imposer les siennes.
- Modifier le minimum de fichiers nécessaire ; pas de refactoring non demandé.
- Si une demande est ambiguë, poser une question plutôt que de deviner.
- Après chaque modification significative, résumer : fichiers touchés, décisions prises, tests ajoutés.
- Ne jamais exécuter de commandes destructrices (`rm -rf`, reset de DB, force push) sans validation explicite.
- Répondre en Français
