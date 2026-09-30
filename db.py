"""SQLite MVP persistence; production Postgres can replace this repository layer."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path: str = ".sourcemap/sourcemap.db"):
        self.path = path
        if path != ":memory:":
            Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def connect(self):
        db = sqlite3.connect(self.path, check_same_thread=False)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _init(self):
        with self.connect() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, github_login TEXT UNIQUE, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
              CREATE TABLE IF NOT EXISTS repos (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, full_name TEXT NOT NULL, clone_url TEXT NOT NULL, is_private INTEGER NOT NULL DEFAULT 0, indexed_revision TEXT, status TEXT NOT NULL DEFAULT 'connected', created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(owner_id, full_name));
              CREATE TABLE IF NOT EXISTS query_logs (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, repo_id TEXT REFERENCES repos(id) ON DELETE SET NULL, query TEXT NOT NULL, response_json TEXT NOT NULL, tokens_used INTEGER NOT NULL DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
              CREATE TABLE IF NOT EXISTS usage_monthly (owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, month TEXT NOT NULL, tokens_used INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(owner_id, month));
            """)

    def upsert_user(self, user_id: str, login: str):
        with self.connect() as db:
            db.execute("INSERT INTO users(id,github_login) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET github_login=excluded.github_login", (user_id, login))

    def connect_repo(self, repo_id: str, owner_id: str, full_name: str, clone_url: str, private: bool):
        with self.connect() as db:
            db.execute("INSERT INTO repos(id,owner_id,full_name,clone_url,is_private) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET full_name=excluded.full_name,clone_url=excluded.clone_url,is_private=excluded.is_private", (repo_id, owner_id, full_name, clone_url, int(private)))

    def list_repos(self, owner_id: str) -> list[dict]:
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT id,full_name,is_private,indexed_revision,status,created_at FROM repos WHERE owner_id=? ORDER BY created_at", (owner_id,))]

    def get_repo(self, repo_id: str, owner_id: str):
        with self.connect() as db:
            row = db.execute("SELECT * FROM repos WHERE id=? AND owner_id=?", (repo_id, owner_id)).fetchone()
            return dict(row) if row else None

    def save_query(self, query_id: str, owner_id: str, repo_id: str | None, query: str, response: dict, tokens: int):
        with self.connect() as db:
            db.execute("INSERT INTO query_logs(id,owner_id,repo_id,query,response_json,tokens_used) VALUES(?,?,?,?,?,?)", (query_id, owner_id, repo_id, query, json.dumps(response), tokens))

    def get_query(self, query_id: str, owner_id: str):
        with self.connect() as db:
            row = db.execute("SELECT * FROM query_logs WHERE id=? AND owner_id=?", (query_id, owner_id)).fetchone()
            if not row:
                return None
            data = dict(row); data["response"] = json.loads(data.pop("response_json")); return data

    def add_usage(self, owner_id: str, month: str, tokens: int) -> int:
        with self.connect() as db:
            db.execute("INSERT INTO usage_monthly(owner_id,month,tokens_used) VALUES(?,?,?) ON CONFLICT(owner_id,month) DO UPDATE SET tokens_used=tokens_used+excluded.tokens_used", (owner_id, month, tokens))
            return db.execute("SELECT tokens_used FROM usage_monthly WHERE owner_id=? AND month=?", (owner_id, month)).fetchone()[0]

    def delete_repo(self, repo_id: str, owner_id: str) -> bool:
        with self.connect() as db:
            cur = db.execute("DELETE FROM repos WHERE id=? AND owner_id=?", (repo_id, owner_id))
            return cur.rowcount > 0
