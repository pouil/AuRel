import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from aurel.run_store import RunStore


CONFIG = {"model": "fixture-model@revision", "task": "transcription"}


class RunStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / "run.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def make_store(self, config=CONFIG):
        return RunStore(self.database, "pilot-001", config)

    def register(self, store, source_id="utt-001", repeat_index=0):
        return store.register_request(
            source_id=source_id,
            audio_sha256="a" * 64,
            task="transcription",
            condition={"name": "clean"},
            repeat_index=repeat_index,
        )

    def test_config_change_rejects_existing_run(self):
        store = self.make_store()
        store.close()
        with self.assertRaisesRegex(ValueError, "Run config changed"):
            self.make_store({"model": "different", "task": "transcription"})

    def test_empty_answer_is_a_completed_response(self):
        with self.make_store() as store:
            key = self.register(store)
            attempt = store.start_attempt(key)
            store.complete(key, attempt, "")
            self.assertEqual(store.requests()[0]["status"], "completed")
            self.assertEqual(store.attempt_history(key)[0]["output_text"], "")
            with self.assertRaisesRegex(ValueError, "immutable"):
                store.start_attempt(key)

    def test_retry_records_failure_without_overwriting_attempt(self):
        with self.make_store() as store:
            key = self.register(store)
            first = store.start_attempt(key)
            store.fail(key, first, "temporary loader error")
            second = store.start_attempt(key)
            store.complete(key, second, "recognized words")
            history = store.attempt_history(key)
            self.assertEqual([row["status"] for row in history],
                             ["failed", "completed"])
            self.assertEqual([row["attempt_no"] for row in history], [1, 2])
            self.assertEqual(history[0]["error"], "temporary loader error")

    def test_abrupt_process_exit_recovers_only_unfinished_request(self):
        script = r"""
import os
import sys
from aurel.run_store import RunStore
store = RunStore(sys.argv[1], "pilot-001",
                 {"model": "fixture-model@revision", "task": "transcription"})
digest = "a" * 64
first = store.register_request("utt-001", digest, "transcription", {"name": "clean"})
second = store.register_request("utt-002", "b" * 64, "transcription", {"name": "clean"})
attempt = store.start_attempt(first)
store.complete(first, attempt, "saved before exit")
store.start_attempt(second)
os._exit(17)
"""
        env = os.environ.copy()
        result = subprocess.run([sys.executable, "-c", script, str(self.database)],
                                cwd=Path(__file__).resolve().parents[1],
                                env=env, check=False)
        self.assertEqual(result.returncode, 17)

        with self.make_store() as store:
            self.assertEqual(store.recover_interrupted(), 1)
            by_source = {row["source_id"]: row for row in store.requests()}
            self.assertEqual(by_source["utt-001"]["status"], "completed")
            self.assertEqual(by_source["utt-002"]["status"], "interrupted")
            self.assertEqual(by_source["utt-001"]["attempt_count"], 1)
            pending = store.requests(statuses=("pending", "failed", "interrupted"))
            self.assertEqual([row["source_id"] for row in pending], ["utt-002"])
            retry = store.start_attempt(by_source["utt-002"]["request_key"])
            self.assertEqual(retry, 2)
            store.complete(by_source["utt-002"]["request_key"], retry, "recovered")
            self.assertEqual(
                [row["status"] for row in store.attempt_history(
                    by_source["utt-002"]["request_key"])],
                ["interrupted", "completed"],
            )

    def test_backup_is_integrity_checked_and_does_not_overwrite(self):
        with self.make_store() as store:
            key = self.register(store)
            attempt = store.start_attempt(key)
            store.complete(key, attempt, "answer")
            backup = store.backup_to(self.root / "backup.sqlite3")
            self.assertTrue(backup.exists())
            connection = sqlite3.connect(str(backup))
            try:
                self.assertEqual(
                    connection.execute("PRAGMA integrity_check").fetchone()[0], "ok"
                )
            finally:
                connection.close()
            with self.assertRaises(FileExistsError):
                store.backup_to(backup)


if __name__ == "__main__":
    unittest.main()
