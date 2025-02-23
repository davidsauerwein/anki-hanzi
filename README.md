### Setup

Prerequisites:
- Python, Poetry
- An Anki account
- Google Cloud Application credentials for translations and text-to-speech (TODO: add instructions for google cloud setup)

Setup dependencies
```
poetry install
```

Place your anki credential under `$HOME/.config/anki-hanzi/anki-credentials.txt`. Put the username on the first line and your password on the second.
```
<username>
<password
```

Place your Google application credentials under `$HOME/.config/google-application-credentials.json`. You can download the file from the Google Cloud Console.


### Usage

```
poetry run anki-hanzi <path-to-collection> <deck>
```

If <path-to-collection> does not exist, the script will create it

Check `--help` for other options


### Development

Format code (black, isort)
```
poetry run format
```

Run linters (flake8, mypy, black, isort)
```
poetry run lint
```
