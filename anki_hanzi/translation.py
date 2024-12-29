from pathlib import Path
from typing import Protocol

from google.cloud import translate_v3

from anki_hanzi.google_cloud import language_to_google_language_code, parse_credentials
from anki_hanzi.language import Language


class Translator(Protocol):
    def translate(
        self, text: str, source_language: Language, target_language: Language
    ) -> str: ...


class GoogleTranslator(Translator):
    _client: translate_v3.TranslationServiceClient
    _project_id: str

    def __init__(self, application_credentials: Path):
        credentials, self._project_id = parse_credentials(application_credentials)
        self._client = translate_v3.TranslationServiceClient(credentials=credentials)

    def translate(
        self, text: str, source_language: Language, target_language: Language
    ) -> str:
        result = self._client.translate_text(
            parent=f"projects/{self._project_id}",
            contents=[text],
            source_language_code=language_to_google_language_code(source_language),
            target_language_code=language_to_google_language_code(target_language),
        )
        return result.translations[0].translated_text
