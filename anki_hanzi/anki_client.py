from pathlib import Path
from typing import Iterable, Protocol

from anki.collection import Collection
from anki.notes import Note
from anki.sync import SyncAuth


class AnkiClient(Protocol):
    def sync(self) -> None: ...

    def notes_in_deck(self, deck: str) -> Iterable[Note]: ...

    def update_note(self, note: Note) -> None: ...

    def media_file_exists(self, file_name: str) -> bool: ...

    def delete_media_file(self, file_name: str) -> None: ...

    def add_media_file(self, file_name: str, data: bytes) -> None: ...


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

    def media_file_exists(self, file_name: str) -> bool:
        return self._collection.media.have(file_name)

    def delete_media_file(self, file_name: str) -> None:
        self._collection.media.trash_files([file_name])

    def add_media_file(self, file_name: str, data: bytes) -> None:

        # write_media will just rename the file if it already exists and write it somewhere else
        # Be a bit more cautious here and error out if the file already exists.
        assert not self.media_file_exists(file_name)
        actual_file_name = self._collection.media.write_data(file_name, data)
        assert actual_file_name == file_name
