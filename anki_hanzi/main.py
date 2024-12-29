from argparse import ArgumentParser
from pathlib import Path

from anki_hanzi.anki_client import AnkiClient, AnkiClientImpl
from anki_hanzi.processing import process_chinese_vocabulary_note
from anki_hanzi.translation import GoogleTranslator, Translator

parser = ArgumentParser()
parser.add_argument(
    "--anki-credentials",
    dest="anki_credentials",
    type=Path,
    default=Path.home() / ".config/anki-hanzi/anki-credentials.txt",
    help="Text file containing Anki sync server username on first line and password on second line",
)
parser.add_argument(
    "--google-application-credentials",
    dest="google_application_credentials",
    type=Path,
    default=Path.home() / ".config/anki-hanzi/google-application-credentials.json",
    help="Location of Google Service Account file",
)
parser.add_argument(
    "--force",
    action="store_true",
    help="Process notes even if they are already tagged as processed",
)
parser.add_argument(
    "--overwrite-target-fields",
    dest="overwrite_target_fields",
    action="store_true",
    help="Overwrite target fields even if they have a non-empty value already",
)
parser.add_argument(
    "anki_collection_path",
    type=Path,
    help="Location where the local Anki collection is stored",
)


def process_chinese_vocabulary(
    anki: AnkiClient, translator: Translator, force: bool, overwrite_target_fields: bool
) -> None:
    for note in anki.notes_in_deck("test"):
        process_chinese_vocabulary_note(
            note=note,
            translator=translator,
            force=force,
            overwrite_target_fields=overwrite_target_fields,
        )
        anki.update_note(note)


def parse_anki_credentials(anki_credentials: Path) -> tuple[str, str]:
    with open(anki_credentials) as f:
        lines = f.readlines()
    assert len(lines) == 2
    username = lines[0].strip()
    password = lines[1].strip()
    return username, password


def run(
    anki_username: str,
    anki_password: str,
    anki_collection_path: Path,
    google_application_credentials: Path,
    force: bool,
    overwrite_target_fields: bool,
) -> None:
    anki = AnkiClientImpl(anki_collection_path, anki_username, anki_password)
    translator = GoogleTranslator(
        application_credentials=google_application_credentials
    )
    anki.sync()
    process_chinese_vocabulary(
        anki=anki,
        translator=translator,
        force=force,
        overwrite_target_fields=overwrite_target_fields,
    )
    anki.sync()


def main() -> None:
    args = parser.parse_args()
    anki_username, anki_password = parse_anki_credentials(args.anki_credentials)
    run(
        anki_username,
        anki_password,
        args.anki_collection_path,
        args.google_application_credentials,
        args.force,
        args.overwrite_target_fields,
    )


if __name__ == "__main__":
    main()
