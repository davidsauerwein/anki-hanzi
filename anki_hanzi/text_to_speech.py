import random
from pathlib import Path
from typing import Protocol

from google.cloud import texttospeech as googletts

from anki_hanzi.google_cloud import language_to_google_language_code, parse_credentials
from anki_hanzi.language import Language


class TextToSpeechSynthesizer(Protocol):
    def synthesize_mp3(self, text: str, language: Language) -> bytes: ...


class GoogleTextToSpeechSynthesizer(TextToSpeechSynthesizer):
    _client: googletts.TextToSpeechClient
    _project_id: str

    def __init__(self, application_credentials: Path):
        credentials, self._project_id = parse_credentials(application_credentials)
        self._client = googletts.TextToSpeechClient(credentials=credentials)

    @staticmethod
    def _language_code_to_voice_name(language_code: str) -> str:
        """Return a random premium voice"""
        # Standard voices such as cmn-CN-Standard-A are not included here.
        candidates = {
            "zh-CN": [
                "cmn-CN-Wavenet-A",
                "cmn-CN-Wavenet-B",
                "cmn-CN-Wavenet-C",
                "cmn-CN-Wavenet-D",
            ],
            "zh-TW": ["cmn-TW-Wavenet-A", "cmn-TW-Wavenet-B", "cmn-TW-Wavenet-C"],
        }[language_code]
        return random.choice(candidates)

    @staticmethod
    def _get_voice(language: Language) -> googletts.VoiceSelectionParams:
        language_code = language_to_google_language_code(language)
        voice_name = GoogleTextToSpeechSynthesizer._language_code_to_voice_name(
            language_code
        )
        return googletts.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        )

    def synthesize_mp3(self, text: str, language: Language) -> bytes:
        text_input = googletts.SynthesisInput(text=text)
        response = self._client.synthesize_speech(
            input=text_input,
            voice=GoogleTextToSpeechSynthesizer._get_voice(language),
            audio_config=googletts.AudioConfig(
                audio_encoding=googletts.AudioEncoding.MP3,
            ),
        )
        return response.audio_content
