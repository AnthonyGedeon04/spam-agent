"""Thin wrapper over the Gmail API, authenticated with your own OAuth client."""

import base64
import html
import os
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# gmail.modify lets the agent read and relabel mail. It cannot permanently delete anything.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def get_service(credentials_file: str = "credentials.json", token_file: str = "token.json"):
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def list_message_ids(service, query: str, limit: int) -> list[str]:
    ids, page_token = [], None
    while len(ids) < limit:
        resp = service.users().messages().list(
            userId="me", q=query, maxResults=min(100, limit - len(ids)), pageToken=page_token
        ).execute()
        ids += [m["id"] for m in resp.get("messages", [])]
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")


def _extract_body(payload: dict) -> str:
    """Prefer text/plain; fall back to stripped text/html."""
    plain, rich = [], []

    def walk(part):
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if data and mime == "text/plain":
            plain.append(_decode(data))
        elif data and mime == "text/html":
            rich.append(_decode(data))
        for p in part.get("parts", []) or []:
            walk(p)

    walk(payload)
    if plain:
        return "\n".join(plain)
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", "\n".join(rich), flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def get_email(service, msg_id: str) -> dict:
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
    return {
        "id": msg_id,
        "thread_id": msg["threadId"],
        "label_ids": msg.get("labelIds", []),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "list_unsubscribe": "list-unsubscribe" in headers,
        "auth": headers.get("authentication-results", ""),
        "body": _extract_body(msg["payload"]) or msg.get("snippet", ""),
    }


def ensure_labels(service, names: list[str]) -> dict[str, str]:
    """Return {label name: label id}, creating any label that does not exist yet."""
    existing = {l["name"]: l["id"] for l in service.users().labels().list(userId="me").execute()["labels"]}
    for name in names:
        if name not in existing:
            # Gmail needs the parent of a nested label ("a/b") to exist first.
            parts = name.split("/")
            for i in range(1, len(parts) + 1):
                partial = "/".join(parts[:i])
                if partial not in existing:
                    created = service.users().labels().create(
                        userId="me", body={"name": partial, "labelListVisibility": "labelShow",
                                           "messageListVisibility": "show"}
                    ).execute()
                    existing[partial] = created["id"]
    return {n: existing[n] for n in names}


def modify_thread(service, thread_id: str, add: list[str], remove: list[str]) -> None:
    service.users().threads().modify(
        userId="me", id=thread_id, body={"addLabelIds": add, "removeLabelIds": remove}
    ).execute()
