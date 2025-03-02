import logging
import os
from argparse import ArgumentParser
from pathlib import Path
from typing import TypedDict

from anki_hanzi import google_cloud
from anki_hanzi.anki_client import AnkiClient, AnkiClientImpl
from anki_hanzi.processing import process_chinese_vocabulary_note
from anki_hanzi.text_to_speech import (
    GoogleTextToSpeechSynthesizer,
    TextToSpeechSynthesizer,
)
from anki_hanzi.translation import GoogleTranslator, Translator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

parser = ArgumentParser()
parser.add_argument(
    "--anki-credentials",
    dest="anki_credentials",
    type=Path,
    default=Path.home() / ".config/anki-hanzi/anki-credentials.txt",
    help="Text file containing Anki sync server username on first line and password on second line",
)
google_application_credentials_default_path = (
    Path.home() / ".config/anki-hanzi/google-application-credentials.json"
)
parser.add_argument(
    "--google-application-credentials",
    dest="google_application_credentials",
    type=Path,
    help=f"Location of Google Service Account file. If not provided the file specified by GOOGLE_APPLICATION_CREDENTIALS is used. If the variable does not exist either, {google_application_credentials_default_path} is used.",
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
parser.add_argument(
    "deck_name",
    type=str,
    help="Name of the deck to process",
)


class ProcessingStats(TypedDict):
    total: int
    modified: int


def process_chinese_vocabulary(
    anki: AnkiClient,
    deck_name: str,
    translator: Translator,
    tts_synthesizer: TextToSpeechSynthesizer,
    force: bool,
    overwrite_target_fields: bool,
) -> ProcessingStats:
    total = 0
    modified = 0

    for note in anki.notes_in_deck(deck_name):
        total += 1
        note_modified = process_chinese_vocabulary_note(
            note=note,
            anki=anki,
            translator=translator,
            tts_synthesizer=tts_synthesizer,
            force=force,
            overwrite_target_fields=overwrite_target_fields,
        )

        if note_modified:
            anki.update_note(note)
            modified += 1

    return {
        "total": total,
        "modified": modified,
    }


def parse_anki_credentials(anki_credentials: Path) -> tuple[str, str]:
    with open(anki_credentials) as f:
        lines = f.readlines()
    assert len(lines) == 2
    username = lines[0].strip()
    password = lines[1].strip()
    return username, password


class AnkiDeckNotFoundException(Exception):
    pass


def run(
    anki_username: str,
    anki_password: str,
    anki_collection_path: Path,
    deck_name: str,
    google_cloud_project_id: str,
    force: bool,
    overwrite_target_fields: bool,
) -> ProcessingStats:
    anki = AnkiClientImpl(anki_collection_path, anki_username, anki_password)
    translator = GoogleTranslator(google_cloud_project_id)
    tts_synthesizer = GoogleTextToSpeechSynthesizer(google_cloud_project_id)

    anki.sync()

    if not anki.deck_exists(deck_name):
        raise AnkiDeckNotFoundException()

    stats = process_chinese_vocabulary(
        anki=anki,
        deck_name=deck_name,
        translator=translator,
        tts_synthesizer=tts_synthesizer,
        force=force,
        overwrite_target_fields=overwrite_target_fields,
    )

    anki.sync()

    logger.info(f"Success: {stats['modified']} / {stats['total']} notes modified.")
    return stats


def main() -> None:
    args = parser.parse_args()
    anki_username, anki_password = parse_anki_credentials(args.anki_credentials)

    if args.google_application_credentials is not None:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
            args.google_application_credentials
        )
    elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS") is None:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
            google_application_credentials_default_path
        )

    google_cloud_project_id = google_cloud.project_id_from_application_credentials(
        Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
    )

    run(
        anki_username,
        anki_password,
        args.anki_collection_path,
        args.deck_name,
        google_cloud_project_id,
        args.force,
        args.overwrite_target_fields,
    )


if __name__ == "__main__":
    main()
