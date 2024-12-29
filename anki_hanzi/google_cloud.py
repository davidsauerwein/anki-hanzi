import json
from pathlib import Path

from google.oauth2 import service_account

from anki_hanzi.language import Language


def parse_credentials(
    application_credentials: Path,
) -> tuple[service_account.Credentials, str]:
    """Parse gcloud application credentials and return Credentials object and project id"""
    with open(application_credentials) as f:
        application_config = json.load(f)
    project_id = application_config["project_id"]
    credentials = service_account.Credentials.from_service_account_file(
        application_credentials  # type: ignore
    )
    return credentials, project_id


def language_to_google_language_code(language: Language) -> str:
    return {
        "Chinese_Simplified": "zh-CN",
        "Chinese_Traditional": "zh-TW",
    }[language]
