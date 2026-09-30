"""GitHub OAuth and repository operations (credentials required for live use)."""

from __future__ import annotations

import json
import secrets
import urllib.error
import urllib.parse
import urllib.request


GITHUB_API = "https://api.github.com"
GITHUB_OAUTH = "https://github.com/login/oauth"


def authorization_url(client_id: str, callback_url: str) -> tuple[str, str]:
    if not client_id:
        raise ValueError("GITHUB_CLIENT_ID is not configured")
    state = secrets.token_urlsafe(24)
    query = urllib.parse.urlencode({"client_id": client_id, "redirect_uri": callback_url, "scope": "read:user repo", "state": state})
    return f"{GITHUB_OAUTH}/authorize?{query}", state


def _request(url: str, token: str | None = None, data: dict | None = None):
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "SourceMap-Prototype"}
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read())


def exchange_code(client_id: str, client_secret: str, code: str):
    return _request(f"{GITHUB_OAUTH}/access_token", data={"client_id": client_id, "client_secret": client_secret, "code": code})


def github_user(token: str):
    return _request(f"{GITHUB_API}/user", token)


def list_repositories(token: str):
    items = _request(f"{GITHUB_API}/user/repos?per_page=100&sort=updated", token)
    return [{"id": str(r["id"]), "full_name": r["full_name"], "clone_url": r["clone_url"], "private": bool(r["private"]), "default_branch": r.get("default_branch", "main")} for r in items]
