import logging
import os
import sys
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Iterable, Iterator, Protocol

from anki.collection import Collection
from anki.notes import Note
from anki.sync import SyncAuth
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@contextmanager
def suppress_stdout() -> Iterator[None]:
    """Redirect stdout to devnull while this context manager is active."""
    original_stdout = sys.stdout
    with open(os.devnull, "w") as devnull:
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = original_stdout


class AnkiClient(Protocol):
    def sync(self) -> None: ...

    def notes_in_deck(self, deck: str) -> Iterable[Note]: ...

    def update_note(self, note: Note) -> None: ...

    def media_file_exists(self, file_name: str) -> bool: ...

    def delete_media_file(self, file_name: str) -> None: ...

    def add_media_file(self, file_name: str, data: bytes) -> None: ...


class AnkiClientException(Exception):
    pass


def escape_media_file_name(file_name: str) -> str:
    return file_name.strip().replace("?", "")


class MediaSyncInProgressException(Exception):
    pass


class AnkiClientImpl(AnkiClient):
    _username: str
    _password: str
    _auth: SyncAuth
    _collection: Collection

    def __init__(self, collection_path: Path, username: str, password: str):
        # This also works if the file does not exist, yet. The constructor will set up an empty database.
        # The initial sync/download is handled by sync()
        self._collection = Collection(path=str(collection_path))

        self._username = username
        self._password = password
        self.init_auth()

    def init_auth(self, endpoint: str = "https://sync.ankiweb.net/") -> None:
        with suppress_stdout():
            # This function is very noisy. It prints stacks traces on stdout just because some function call takes
            # longer than 100 ms. This is nothing we care about. For lack of a better mechanism to control these logs,
            # completely silence all writes to stdout preformed by this function.
            self._auth = self._collection.sync_login(
                username=self._username,
                password=self._password,
                endpoint=endpoint,
            )

    @retry(
        wait=wait_exponential(min=timedelta(seconds=1), max=timedelta(seconds=30)),
        stop=stop_after_attempt(50),
    )
    def wait_for_media_sync(self) -> None:
        # If still active raise and let tenacity handle the retries
        # After 50 attempts we abort
        if self._collection.media_sync_status().active:
            raise MediaSyncInProgressException()

    def sync(self) -> None:
        with suppress_stdout():
            # This function is very noisy, just like self._collection.sync_login()
            sync_result = self._collection.sync_collection(
                auth=self._auth, sync_media=True
            )

        if sync_result.required == sync_result.FULL_DOWNLOAD:
            # Initial sync. Download everything.
            logger.info(
                "Performing initial sync (full download). This may take a while depending on how much media your collection has."
            )

            # We need to re-initialize the auth object using the new endpoint, otherwise we get 400 responses saying
            # "missing original size".
            # See Anki-Android who ran into the same problem:
            # - Issue: https://github.com/ankidroid/Anki-Android/issues/14219
            # - Fix: https://github.com/ankidroid/Anki-Android/pull/14935/commits/f90c1d87ddb5aaa23fa89ee28bca5335ff673971
            assert sync_result.new_endpoint
            self.init_auth(sync_result.new_endpoint)

            self._collection.close_for_full_sync()
            with suppress_stdout():
                self._collection.full_upload_or_download(
                    auth=self._auth,
                    server_usn=sync_result.server_media_usn,
                    upload=False,
                )
            self._collection.reopen(after_full_sync=True)
        elif sync_result.required != sync_result.NO_CHANGES:
            # From what I have observed this returns NO_CHANGES on every regular sync. Anything else means conflicts
            # which cannot be resolved here.
            raise AnkiClientException(
                f"Unexpected or unsupported sync result: {sync_result}"
            )

        # Media is synced in the background. That means that the call to sync_collection started the media sync, but
        # there is no guarantee it has actually completed. Wait until the sync is done.
        self.wait_for_media_sync()

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
        if self.media_file_exists(file_name):
            raise AnkiClientException(
                f"Requested media file already exists: {file_name}"
            )

        actual_file_name = self._collection.media.write_data(file_name, data)

        if actual_file_name != file_name:
            raise AnkiClientException(
                f"Actual file name not equal despite requested file name not existing. Requested: {file_name} Actual: {actual_file_name}"
            )
