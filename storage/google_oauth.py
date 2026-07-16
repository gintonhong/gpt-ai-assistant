from __future__ import annotations

import secrets
from threading import Lock

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from config.settings import (
    GOOGLE_OAUTH_CLIENT_ID,
    GOOGLE_OAUTH_CLIENT_SECRET,
    GOOGLE_OAUTH_REDIRECT_URI,
)


SCOPES = [
    "https://www.googleapis.com/auth/drive.file"
]

_state_lock = Lock()
_pending_flows: dict[str, str] = {}


def _client_config() -> dict:
    if not GOOGLE_OAUTH_CLIENT_ID:
        raise RuntimeError(
            "GOOGLE_OAUTH_CLIENT_ID is not configured."
        )

    if not GOOGLE_OAUTH_CLIENT_SECRET:
        raise RuntimeError(
            "GOOGLE_OAUTH_CLIENT_SECRET is not configured."
        )

    return {
        "web": {
            "client_id": GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                GOOGLE_OAUTH_REDIRECT_URI
            ],
        }
    }


def _flow(
    *,
    state: str | None = None,
    code_verifier: str | None = None,
) -> Flow:
    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        state=state,
        redirect_uri=GOOGLE_OAUTH_REDIRECT_URI,
        autogenerate_code_verifier=False,
    )

    if code_verifier:
        flow.code_verifier = code_verifier

    return flow


def create_authorization_url() -> str:
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)

    flow = _flow(
        state=state,
        code_verifier=code_verifier,
    )

    authorization_url, returned_state = (
        flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
    )

    with _state_lock:
        _pending_flows[
            returned_state
        ] = code_verifier

    return authorization_url


def exchange_callback(
    *,
    authorization_response: str,
    state: str,
) -> dict:
    with _state_lock:
        code_verifier = _pending_flows.pop(
            state,
            None,
        )

    if not code_verifier:
        raise RuntimeError(
            "Invalid or expired OAuth state."
        )

    flow = _flow(
        state=state,
        code_verifier=code_verifier,
    )

    flow.fetch_token(
        authorization_response=authorization_response,
        code_verifier=code_verifier,
    )

    credentials = flow.credentials

    if not credentials.refresh_token:
        raise RuntimeError(
            "Google did not return a refresh token. "
            "Revoke the app authorization and try again."
        )

    drive = build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    created = (
        drive.files()
        .create(
            body={
                "name": "LINE_AI_Attachments",
                "mimeType": (
                    "application/vnd.google-apps.folder"
                ),
            },
            fields="id,name,webViewLink",
        )
        .execute()
    )

    return {
        "refresh_token": (
            credentials.refresh_token
        ),
        "folder_id": created["id"],
        "folder_name": created["name"],
        "folder_web_view_link": (
            created.get("webViewLink")
        ),
    }
