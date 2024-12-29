import json
from pathlib import Path
from typing import Literal, Protocol

from google.cloud import translate_v3
from google.oauth2 import service_account

Language = Literal["Chinese_Simplified", "Chinese_Traditional"]


class Translator(Protocol):
    def translate(
        self, text: str, source_language: Language, target_language: Language
    ) -> str: ...


class GoogleTranslator(Translator):
    _client: translate_v3.TranslationServiceClient
    _project_id: str

    def __init__(self, application_credentials: Path):
        with open(application_credentials) as f:
            application_config = json.load(f)
        self._project_id = application_config["project_id"]
        credentials = service_account.Credentials.from_service_account_file(
            application_credentials  # type: ignore
        )
        self._client = translate_v3.TranslationServiceClient(credentials=credentials)

    @staticmethod
    def _language_to_google_language_code(language: str) -> str:
        return {
            "Chinese_Simplified": "zh-CN",
            "Chinese_Traditional": "zh-TW",
        }[language]

    def translate(
        self, text: str, source_language: Language, target_language: Language
    ) -> str:
        result = self._client.translate_text(
            parent=f"projects/{self._project_id}",
            contents=[text],
            source_language_code=GoogleTranslator._language_to_google_language_code(
                source_language
            ),
            target_language_code=GoogleTranslator._language_to_google_language_code(
                target_language
            ),
        )
        return result.translations[0].translated_text
