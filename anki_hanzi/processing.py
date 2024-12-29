from functools import partial
from typing import Callable

from anki.notes import Note
from dragonmapper import hanzi  # type: ignore

from anki_hanzi.anki_client import AnkiClient
from anki_hanzi.text_to_speech import Language, TextToSpeechSynthesizer
from anki_hanzi.translation import Translator

ANKI_HANZI_TAG = "anki-hanzi"


def to_pinyin(text: str) -> str:
    return hanzi.to_pinyin(text, accented=True)  # type: ignore


def to_zhuyin(text: str) -> str:
    return hanzi.to_zhuyin(text)  # type: ignore


def synthesize(
    text: str,
    anki: AnkiClient,
    synthesizer: TextToSpeechSynthesizer,
    language: Language,
    overwrite_target_field: bool,
) -> str:
    mp3 = synthesizer.synthesize_mp3(text, language)
    file_name = f"{text}.mp3"
    if overwrite_target_field and anki.media_file_exists(file_name):
        anki.delete_media_file(file_name)
    anki.add_media_file(file_name, mp3)
    return f"[sound:{file_name}]"


def transform_field(
    note: Note,
    source_field: str,
    target_field: str,
    transformation_function: Callable[[str], str],
    overwrite_target_field: bool = False,
) -> bool:
    assert source_field in note and target_field in note

    if not note[source_field]:
        # Ignore the transformation if source is empty
        return False

    if note[target_field] and not overwrite_target_field:
        # Do not overwrite target fields unless explicitly asked.
        return False

    note[target_field] = transformation_function(note[source_field])
    return False


def process_chinese_vocabulary_note(
    note: Note,
    anki: AnkiClient,
    translator: Translator,
    tts_synthesizer: TextToSpeechSynthesizer,
    force: bool = False,
    overwrite_target_fields: bool = False,
) -> bool:
    if not force and note.has_tag(ANKI_HANZI_TAG):
        return False

    transform = partial(
        transform_field, note=note, overwrite_target_field=overwrite_target_fields
    )

    simplified_to_traditional = partial(
        translator.translate,
        source_language="Chinese_Simplified",
        target_language="Chinese_Traditional",
    )
    traditional_to_simplified = partial(
        translator.translate,
        source_language="Chinese_Traditional",
        target_language="Chinese_Simplified",
    )
    synthesize_simplified = partial(
        synthesize,
        anki=anki,
        synthesizer=tts_synthesizer,
        language="Chinese_Simplified",
        overwrite_target_field=overwrite_target_fields,
    )

    transform(
        source_field="Word (Character)",
        target_field="Word (Traditional Character)",
        transformation_function=simplified_to_traditional,
    )
    transform(
        source_field="Word (Traditional Character)",
        target_field="Word (Character)",
        transformation_function=traditional_to_simplified,
    )
    transform(
        source_field="Example Sentence - Characters",
        target_field="Example Sentence - Traditional Characters",
        transformation_function=simplified_to_traditional,
    )
    transform(
        source_field="Example Sentence - Traditional Characters",
        target_field="Example Sentence - Characters",
        transformation_function=traditional_to_simplified,
    )
    transform(
        source_field="Word (Traditional Character)",
        target_field="Word (Pinyin)",
        transformation_function=to_pinyin,
    )
    transform(
        source_field="Word (Traditional Character)",
        target_field="Word (Zhuyin)",
        transformation_function=to_zhuyin,
    )
    transform(
        source_field="Example Sentence - Traditional Characters",
        target_field="Example Sentence - Zhuyin",
        transformation_function=to_zhuyin,
    )
    transform(
        source_field="Word (Character)",
        target_field="Generated Speech",
        transformation_function=synthesize_simplified,
    )
    transform(
        source_field="Example Sentence - Characters",
        target_field="Example Sentence - Generated  Speech",
        transformation_function=synthesize_simplified,
    )

    note.add_tag(ANKI_HANZI_TAG)
    return True
