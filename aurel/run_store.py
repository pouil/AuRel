"""SQLite per-example run ledger with transactional retries and recovery."""

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from aurel.fingerprint import fingerprint


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      allow_nan=False, separators=(",", ":"))


class RunStore:
    """Single-writer ledger for one immutable run specification.

    Call recover_interrupted() after reopening a run, before scheduling retries.
    Each attempt and its request status are committed atomically.
    """

    def __init__(self, database, run_id, config):
        if type(run_id) is not str or not run_id.strip():
            raise ValueError("run_id must be a nonempty string")
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.config_json = _json(config)
        self.config_fingerprint = fingerprint(config)
        self.connection = sqlite3.connect(str(self.path), timeout=30,
                                          isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA synchronous = FULL")
        self._create_schema()
        self._check_run_config()

    def _create_schema(self):
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                config_json TEXT NOT NULL,
                config_fingerprint TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS requests (
                run_id TEXT NOT NULL,
                request_key TEXT NOT NULL,
                source_id TEXT NOT NULL,
                audio_sha256 TEXT NOT NULL,
                task TEXT NOT NULL,
                condition_json TEXT NOT NULL,
                repeat_index INTEGER NOT NULL CHECK (repeat_index >= 0),
                status TEXT NOT NULL CHECK (
                    status IN ('pending','running','completed','failed','interrupted')
                ),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (run_id, request_key),
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            );
            CREATE TABLE IF NOT EXISTS attempts (
                run_id TEXT NOT NULL,
                request_key TEXT NOT NULL,
                attempt_no INTEGER NOT NULL CHECK (attempt_no > 0),
                status TEXT NOT NULL CHECK (
                    status IN ('running','completed','failed','interrupted')
                ),
                started_at TEXT NOT NULL,
                finished_at TEXT,
                output_text TEXT,
                error TEXT,
                PRIMARY KEY (run_id, request_key, attempt_no),
                FOREIGN KEY (run_id, request_key)
                    REFERENCES requests(run_id, request_key)
            );
            CREATE INDEX IF NOT EXISTS attempts_by_status
                ON attempts(run_id, status);
        """)
        self.connection.execute("PRAGMA user_version = 1")

    def _check_run_config(self):
        with self._transaction():
            row = self.connection.execute(
                "SELECT config_json, config_fingerprint FROM runs WHERE run_id = ?",
                (self.run_id,),
            ).fetchone()
            if row is None:
                self.connection.execute(
                    "INSERT INTO runs VALUES (?, ?, ?, ?)",
                    (self.run_id, self.config_json,
                     self.config_fingerprint, _utc_now()),
                )
            elif (row["config_fingerprint"] != self.config_fingerprint
                  or row["config_json"] != self.config_json):
                raise ValueError(
                    "Run config changed; create a new run instead of reusing results"
                )

    @contextmanager
    def _transaction(self):
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.connection.execute("COMMIT")
        except BaseException:
            self.connection.execute("ROLLBACK")
            raise

    def register_request(self, source_id, audio_sha256, task, condition,
                         repeat_index=0):
        """Register a stable request and return its config-bound request key."""
        if type(source_id) is not str or not source_id.strip():
            raise ValueError("source_id must be a nonempty string")
        if type(audio_sha256) is not str or not _SHA256.fullmatch(audio_sha256):
            raise ValueError("audio_sha256 must be a lowercase SHA-256 hex digest")
        if type(task) is not str or not task.strip():
            raise ValueError("task must be a nonempty string")
        if type(repeat_index) is not int or repeat_index < 0:
            raise ValueError("repeat_index must be a nonnegative integer")
        condition_json = _json(condition)
        # Validate nested condition values using the same strict JSON rules.
        condition_fingerprint = fingerprint({"condition": condition})
        request_key = fingerprint({
            "run_config_fingerprint": self.config_fingerprint,
            "source_id": source_id,
            "audio_sha256": audio_sha256,
            "task": task,
            "condition_fingerprint": condition_fingerprint,
            "repeat_index": repeat_index,
        })
        now = _utc_now()
        with self._transaction():
            row = self.connection.execute(
                "SELECT source_id, audio_sha256, task, condition_json, repeat_index "
                "FROM requests WHERE run_id = ? AND request_key = ?",
                (self.run_id, request_key),
            ).fetchone()
            values = (source_id, audio_sha256, task, condition_json, repeat_index)
            if row is not None:
                saved = tuple(row[key] for key in (
                    "source_id", "audio_sha256", "task", "condition_json",
                    "repeat_index",
                ))
                if saved != values:
                    raise ValueError("Request key collision or inconsistent request")
                return request_key
            self.connection.execute(
                "INSERT INTO requests VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
                (self.run_id, request_key, source_id, audio_sha256, task,
                 condition_json, repeat_index, now, now),
            )
        return request_key

    def start_attempt(self, request_key):
        """Start the next attempt; completed or already-running rows are rejected."""
        now = _utc_now()
        with self._transaction():
            row = self.connection.execute(
                "SELECT status FROM requests WHERE run_id = ? AND request_key = ?",
                (self.run_id, request_key),
            ).fetchone()
            if row is None:
                raise KeyError("Unknown request_key")
            if row["status"] == "completed":
                raise ValueError("Completed requests are immutable")
            if row["status"] == "running":
                raise ValueError("Request already has a running attempt")
            previous = self.connection.execute(
                "SELECT COALESCE(MAX(attempt_no), 0) AS n FROM attempts "
                "WHERE run_id = ? AND request_key = ?",
                (self.run_id, request_key),
            ).fetchone()["n"]
            attempt_no = previous + 1
            self.connection.execute(
                "INSERT INTO attempts VALUES (?, ?, ?, 'running', ?, NULL, NULL, NULL)",
                (self.run_id, request_key, attempt_no, now),
            )
            self.connection.execute(
                "UPDATE requests SET status = 'running', updated_at = ? "
                "WHERE run_id = ? AND request_key = ?",
                (now, self.run_id, request_key),
            )
        return attempt_no

    def complete(self, request_key, attempt_no, output_text):
        """Commit a successful model response, including an empty string."""
        if type(output_text) is not str:
            raise ValueError("output_text must be a string")
        self._finish(request_key, attempt_no, "completed",
                     output_text=output_text)

    def fail(self, request_key, attempt_no, error):
        """Commit an execution failure separately from a model response."""
        if type(error) is not str or not error:
            raise ValueError("error must be a nonempty string")
        self._finish(request_key, attempt_no, "failed", error=error)

    def _finish(self, request_key, attempt_no, status, output_text=None, error=None):
        now = _utc_now()
        with self._transaction():
            row = self.connection.execute(
                "SELECT status FROM attempts WHERE run_id = ? AND request_key = ? "
                "AND attempt_no = ?",
                (self.run_id, request_key, attempt_no),
            ).fetchone()
            if row is None:
                raise KeyError("Unknown attempt")
            if row["status"] != "running":
                raise ValueError("Only a running attempt can be completed")
            self.connection.execute(
                "UPDATE attempts SET status = ?, finished_at = ?, output_text = ?, "
                "error = ? WHERE run_id = ? AND request_key = ? AND attempt_no = ?",
                (status, now, output_text, error, self.run_id, request_key, attempt_no),
            )
            self.connection.execute(
                "UPDATE requests SET status = ?, updated_at = ? "
                "WHERE run_id = ? AND request_key = ?",
                (status, now, self.run_id, request_key),
            )

    def recover_interrupted(self):
        """Mark committed running attempts as interrupted; safe after process exit."""
        now = _utc_now()
        with self._transaction():
            rows = self.connection.execute(
                "SELECT request_key, attempt_no FROM attempts "
                "WHERE run_id = ? AND status = 'running'",
                (self.run_id,),
            ).fetchall()
            for row in rows:
                self.connection.execute(
                    "UPDATE attempts SET status = 'interrupted', finished_at = ? "
                    "WHERE run_id = ? AND request_key = ? AND attempt_no = ?",
                    (now, self.run_id, row["request_key"], row["attempt_no"]),
                )
                self.connection.execute(
                    "UPDATE requests SET status = 'interrupted', updated_at = ? "
                    "WHERE run_id = ? AND request_key = ?",
                    (now, self.run_id, row["request_key"]),
                )
        return len(rows)

    def requests(self, statuses=None):
        query = (
            "SELECT r.request_key, r.source_id, r.audio_sha256, r.task, "
            "r.condition_json, r.repeat_index, r.status, "
            "COUNT(a.attempt_no) AS attempt_count "
            "FROM requests r LEFT JOIN attempts a "
            "ON a.run_id = r.run_id AND a.request_key = r.request_key "
            "WHERE r.run_id = ?"
        )
        params = [self.run_id]
        if statuses:
            values = tuple(statuses)
            if not values:
                return []
            query += " AND r.status IN (" + ",".join("?" for _ in values) + ")"
            params.extend(values)
        query += " GROUP BY r.run_id, r.request_key ORDER BY r.request_key"
        rows = self.connection.execute(query, params).fetchall()
        return [{
            "request_key": row["request_key"],
            "source_id": row["source_id"],
            "audio_sha256": row["audio_sha256"],
            "task": row["task"],
            "condition": json.loads(row["condition_json"]),
            "repeat_index": row["repeat_index"],
            "status": row["status"],
            "attempt_count": row["attempt_count"],
        } for row in rows]

    def attempt_history(self, request_key):
        rows = self.connection.execute(
            "SELECT attempt_no, status, started_at, finished_at, output_text, error "
            "FROM attempts WHERE run_id = ? AND request_key = ? "
            "ORDER BY attempt_no",
            (self.run_id, request_key),
        ).fetchall()
        return [dict(row) for row in rows]

    def backup_to(self, destination):
        """Create a new verified SQLite backup; refuses to overwrite an artifact."""
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.resolve() == self.path.resolve():
            raise ValueError("Backup destination must differ from the live database")
        if destination.exists():
            raise FileExistsError(str(destination))
        backup_connection = sqlite3.connect(str(destination))
        try:
            self.connection.backup(backup_connection)
            result = backup_connection.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise sqlite3.DatabaseError("Backup integrity check failed: " + result)
        except BaseException:
            backup_connection.close()
            destination.unlink(missing_ok=True)
            raise
        else:
            backup_connection.close()
        return destination

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
