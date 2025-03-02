import json
from pathlib import Path

from anki_hanzi.language import Language


def project_id_from_application_credentials(
    application_credentials: Path,
) -> str:
    """Parse gcloud application credentials and return project id"""
    with open(application_credentials) as f:
        credentials = json.load(f)
    project_id: str = credentials["project_id"]
    return project_id


def language_to_google_language_code(language: Language) -> str:
    return {
        "Chinese_Simplified": "zh-CN",
        "Chinese_Traditional": "zh-TW",
        "English": "en",
    }[language]
