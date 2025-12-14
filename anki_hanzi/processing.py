from functools import partial
from typing import Callable

from anki.notes import Note
from bs4 import BeautifulSoup
from dragonmapper import hanzi  # type: ignore

from anki_hanzi.anki_client import AnkiClient, escape_media_file_name
from anki_hanzi.language import Language
from anki_hanzi.text_to_speech import TextToSpeechSynthesizer
from anki_hanzi.translation import Translator

ANKI_HANZI_TAG = "anki-hanzi"


def to_pinyin(text: str) -> str:
    return hanzi.to_pinyin(text, accented=True)  # type: ignore


def to_zhuyin(text: str) -> str:
    return hanzi.to_zhuyin(text)  # type: ignore


def to_tones(text: str) -> str:
    numbered_pinyin: str = hanzi.to_pinyin(text, accented=False)
    tones = [char for char in numbered_pinyin if char.isdigit()]
    return "".join(tones)


def strip_html_tags(text: str) -> str:
    # Sometimes some html tags stay in the string due to copy-paste. Remove
    # those as they can end up in unexpected results such as wrong media file
    # names.
    return BeautifulSoup(text, "html.parser").get_text()


def synthesize(
    text: str,
    anki: AnkiClient,
    synthesizer: TextToSpeechSynthesizer,
    language: Language,
    overwrite_target_field: bool,
) -> str:
    text = text.strip()
    if not text:
        raise ValueError(
            "Text to synthesize should contain something. "
            "Does the input contain odd formatting that causes all contents to get stripped on error?"
        )

    file_name = f"{text}.mp3"
    file_name = escape_media_file_name(file_name)
    result = f"[sound:{file_name}]"

    if anki.media_file_exists(file_name):
        if not overwrite_target_field:
            return result
        else:
            anki.delete_media_file(file_name)

    mp3 = synthesizer.synthesize_mp3(text, language)
    anki.add_media_file(file_name, mp3)
    return result


def transform_field(
    note: Note,
    source_field: str,
    target_field: str,
    transformation_function: Callable[[str], str],
    overwrite_target_field: bool = False,
) -> bool:
    """Take a source_field as input, process its contents with transformation_function and write result to target_field."""
    assert source_field in note and target_field in note

    if not note[source_field]:
        # Ignore the transformation if source is empty
        return False

    if note[target_field] and not overwrite_target_field:
        # Do not overwrite target fields unless explicitly asked.
        return False

    source_text = note[source_field]
    source_text = strip_html_tags(source_text)
    note[target_field] = transformation_function(source_text)
    return True


def modify_field(
    note: Note,
    field: str,
    transformation_function: Callable[[str], str],
) -> bool:
    """Process contents of field with transformation_function and write result back to the same field."""
    assert field in note

    if not note[field]:
        # Ignore empty fields
        return False

    result = transformation_function(note[field])
    modified = result != note[field]
    note[field] = result
    return modified


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
    modify = partial(modify_field, note=note)

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
    traditional_to_english = partial(
        translator.translate,
        source_language="Chinese_Traditional",
        target_language="English",
    )
    synthesize_simplified = partial(
        synthesize,
        anki=anki,
        synthesizer=tts_synthesizer,
        language="Chinese_Simplified",
        overwrite_target_field=overwrite_target_fields,
    )

    modified = False

    # Strip any HTML tags from text fields that could originate from user input.
    # Also strip whitespace
    for field in [
        "Word (Character)",
        "Word (Traditional Character)",
        "Example Sentence - Characters",
        "Example Sentence - Traditional Characters",
    ]:
        modified |= modify(
            field=field,
            transformation_function=strip_html_tags,
        )
        modified |= modify(
            field=field,
            transformation_function=str.strip,
        )

    modified |= transform(
        source_field="Word (Character)",
        target_field="Word (Traditional Character)",
        transformation_function=simplified_to_traditional,
    )
    modified |= transform(
        source_field="Word (Traditional Character)",
        target_field="Word (Character)",
        transformation_function=traditional_to_simplified,
    )
    modified |= transform(
        source_field="Example Sentence - Characters",
        target_field="Example Sentence - Traditional Characters",
        transformation_function=simplified_to_traditional,
    )
    modified |= transform(
        source_field="Example Sentence - Traditional Characters",
        target_field="Example Sentence - Characters",
        transformation_function=traditional_to_simplified,
    )
    modified |= transform(
        source_field="Word (Traditional Character)",
        target_field="Word (Pinyin)",
        transformation_function=to_pinyin,
    )
    modified |= transform(
        source_field="Word (Traditional Character)",
        target_field="Word (Zhuyin)",
        transformation_function=to_zhuyin,
    )
    modified |= transform(
        source_field="Example Sentence - Traditional Characters",
        target_field="Example Sentence - English",
        transformation_function=traditional_to_english,
    )
    modified |= transform(
        source_field="Example Sentence - Traditional Characters",
        target_field="Example Sentence - Pinyin",
        transformation_function=to_pinyin,
    )
    modified |= transform(
        source_field="Example Sentence - Traditional Characters",
        target_field="Example Sentence - Zhuyin",
        transformation_function=to_zhuyin,
    )
    modified |= transform(
        source_field="Word (Character)",
        target_field="Generated Speech",
        transformation_function=synthesize_simplified,
    )
    modified |= transform(
        source_field="Example Sentence - Characters",
        target_field="Example Sentence - Generated  Speech",
        transformation_function=synthesize_simplified,
    )
    modified |= transform(
        source_field="Word (Character)",
        target_field="Word (Tone numbers)",
        transformation_function=to_tones,
    )

    note.add_tag(ANKI_HANZI_TAG)
    return modified
