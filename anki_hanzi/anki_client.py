from pathlib import Path
from typing import Iterable, Protocol

from anki.collection import Collection
from anki.notes import Note
from anki.sync import SyncAuth


class AnkiClient(Protocol):
    def sync(self) -> None: ...

    def notes_in_deck(self, deck: str) -> Iterable[Note]: ...

    def update_note(self, note: Note) -> None: ...


class AnkiClientException(Exception):
    pass


class AnkiClientImpl(AnkiClient):
    _auth: SyncAuth
    _collection: Collection

    def __init__(self, collection_path: Path, username: str, password: str):
        self._collection = Collection(path=str(collection_path))
        self._auth = self._collection.sync_login(
            username=username, password=password, endpoint="https://sync.ankiweb.net/"
        )

    def sync(self) -> None:
        sync_result = self._collection.sync_collection(auth=self._auth, sync_media=True)
        if sync_result.required != sync_result.NO_CHANGES:
            # From what I have observed this returns NO_CHANGES on every regular sync.
            # Was not able to figure out how to make an initial download with collection.full_download_or_upload() work.
            raise AnkiClientException(
                f"Unexpected or unsupported sync result: {sync_result}"
            )

    def deck_exists(self, deck: str) -> bool:
        return self._collection.decks.by_name(deck) is not None

    def notes_in_deck(self, deck: str) -> Iterable[Note]:
        assert self.deck_exists(deck)

        note_ids = self._collection.find_notes(query=f"deck:{deck}")
        for note_id in note_ids:
            yield self._collection.get_note(note_id)

    def update_note(self, note: Note) -> None:
        self._collection.update_note(note)
