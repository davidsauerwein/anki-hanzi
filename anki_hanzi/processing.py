from anki.notes import Note

ANKI_HANZI_TAG = "anki-hanzi"


def process_chinese_vocabulary_note(note: Note, force: bool = False) -> bool:
    print(f"Processing {note}")
    if not force and note.has_tag(ANKI_HANZI_TAG):
        return False
    # TODO Call all the different functions
    # TODO tag notes
    return True
