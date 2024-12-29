from functools import partial
from typing import Callable

from anki.notes import Note
from dragonmapper import hanzi  # type: ignore

from anki_hanzi.translation import Translator

ANKI_HANZI_TAG = "anki-hanzi"


def to_pinyin(text: str) -> str:
    return hanzi.to_pinyin(text, accented=True)  # type: ignore


def to_zhuyin(text: str) -> str:
    return hanzi.to_zhuyin(text)  # type: ignore


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
    translator: Translator,
    force: bool = False,
    overwrite_target_fields: bool = False,
) -> bool:
    if not force and note.has_tag(ANKI_HANZI_TAG):
        return False

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

    transform_field(
        note=note,
        source_field="Word (Character)",
        target_field="Word (Traditional Character)",
        transformation_function=simplified_to_traditional,
        overwrite_target_field=overwrite_target_fields,
    )
    transform_field(
        note=note,
        source_field="Word (Traditional Character)",
        target_field="Word (Character)",
        transformation_function=traditional_to_simplified,
        overwrite_target_field=overwrite_target_fields,
    )
    transform_field(
        note=note,
        source_field="Example Sentence - Characters",
        target_field="Example Sentence - Traditional Characters",
        transformation_function=simplified_to_traditional,
        overwrite_target_field=overwrite_target_fields,
    )
    transform_field(
        note=note,
        source_field="Example Sentence - Traditional Characters",
        target_field="Example Sentence - Characters",
        transformation_function=traditional_to_simplified,
        overwrite_target_field=overwrite_target_fields,
    )
    transform_field(
        note=note,
        source_field="Word (Traditional Character)",
        target_field="Word (Pinyin)",
        transformation_function=to_pinyin,
        overwrite_target_field=overwrite_target_fields,
    )
    transform_field(
        note=note,
        source_field="Word (Traditional Character)",
        target_field="Word (Zhuyin)",
        transformation_function=to_zhuyin,
        overwrite_target_field=overwrite_target_fields,
    )
    transform_field(
        note=note,
        source_field="Example Sentence - Traditional Characters",
        target_field="Example Sentence - Zhuyin",
        transformation_function=to_zhuyin,
        overwrite_target_field=overwrite_target_fields,
    )

    note.add_tag(ANKI_HANZI_TAG)
    return True
