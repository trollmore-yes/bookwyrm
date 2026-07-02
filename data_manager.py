import json
import sqlite3
from pathlib import Path


class DataManager:
    def __init__(self, db_path=None) -> None:
        self.db_path = Path(db_path) if db_path else None

    def set_db_path(self, db_path) -> None:
        self.db_path = Path(db_path) if db_path else None

    def init_database(self, db_path=None) -> Path:
        target_path = Path(db_path) if db_path else self.db_path
        if not target_path:
            raise ValueError("A database path is required")

        target_path.parent.mkdir(parents=True, exist_ok=True)

        if target_path.exists():
            conn = sqlite3.connect(target_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signups'")
            table_exists = cursor.fetchone() is not None
            conn.close()
            if table_exists:
                return target_path

        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()

        migration_file = Path(__file__).resolve().parent / "migrations" / "0001-initial.sql"
        with open(migration_file, "r", encoding="utf-8") as handle:
            cursor.executescript(handle.read())

        conn.commit()
        conn.close()
        return target_path

    def get_db_connection(self, db_path=None):
        target_path = Path(db_path) if db_path else self.db_path
        if not target_path:
            raise ValueError("A database path is required")

        conn = sqlite3.connect(target_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save_signups_to_db(self, timestamp, guild_id, users, naughty_list, db_path=None) -> None:
        target_path = self.init_database(db_path)
        conn = self.get_db_connection(target_path)
        cursor = conn.cursor()

        for user in users:
            if isinstance(user, dict):
                row_timestamp = user.get("timestamp", timestamp)
                name = user.get("name", "")
                words_writing = user.get("words_wr", 0)
                words_reading = user.get("words_r", 0)
                genres_writing = json.dumps(user.get("genre_wr", []))
                genres_reading = json.dumps(user.get("genre_r", []))
                cw_writing = json.dumps(user.get("cw_wr", []))
                cw_veto = json.dumps(user.get("cw_veto", []))
                size_pref = json.dumps(user.get("size_pref", []))
                match_pref_raw = user.get("match_pref", "")
                match_veto_raw = user.get("match_veto", "")
                prev_month = user.get("prev_month", "")
                prev_group = user.get("prev_group", "")
            else:
                row_timestamp = getattr(user, "timestamp", timestamp)
                name = getattr(user, "name", "")
                words_writing = getattr(user, "words_wr", 0)
                words_reading = getattr(user, "words_r", 0)
                genres_writing = json.dumps(getattr(user, "genre_wr", []))
                genres_reading = json.dumps(getattr(user, "genre_r", []))
                cw_writing = json.dumps(getattr(user, "cw_wr", []))
                cw_veto = json.dumps(getattr(user, "cw_veto", []))
                size_pref = json.dumps(getattr(user, "size_pref", []))
                match_pref_raw = getattr(user, "match_pref", "")
                match_veto_raw = getattr(user, "match_veto", "")
                prev_month = getattr(user, "prev_month", "")
                prev_group = getattr(user, "prev_group", "")

            if row_timestamp is None:
                raise ValueError("Each signup row requires a timestamp from the CSV")

            match_pref = json.dumps(match_pref_raw) if isinstance(match_pref_raw, list) else (match_pref_raw or "")
            match_veto = json.dumps(match_veto_raw) if isinstance(match_veto_raw, list) else (match_veto_raw or "")

            cursor.execute(
                """
                INSERT OR REPLACE INTO signups (
                    timestamp, guild_id, name, words_writing, words_reading,
                    genres_writing, genres_reading, cw_writing, cw_veto,
                    size_preference, match_request, match_veto,
                    prev_month_status, prev_group_name, crit_history,
                    completed_book, quiz_passed, chapter_links
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_timestamp,
                    guild_id,
                    name,
                    words_writing,
                    words_reading,
                    genres_writing,
                    genres_reading,
                    cw_writing,
                    cw_veto,
                    size_pref,
                    match_pref,
                    match_veto,
                    prev_month,
                    prev_group,
                    0,
                    0,
                    1,
                    None,
                ),
            )

        conn.commit()
        conn.close()

    def save_groups_to_db(self, timestamp, guild_id, groups, db_path=None) -> None:
        target_path = self.init_database(db_path)
        conn = self.get_db_connection(target_path)
        cursor = conn.cursor()

        for group in groups:
            if isinstance(group, dict):
                mascot = group.get("name", "")
                members = group.get("members", [])
                thread_id = group.get("thread_id", 0)
            else:
                mascot = getattr(group, "name", "")
                members = getattr(group, "members", [])
                thread_id = getattr(group, "thread_id", 0)

            member_names = []
            for member in members:
                if isinstance(member, dict):
                    member_names.append(member.get("name", ""))
                else:
                    member_names.append(getattr(member, "name", ""))

            cursor.execute(
                """
                INSERT OR REPLACE INTO groups (
                    timestamp, guild_id, mascot, thread_id, member_ids
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    guild_id,
                    mascot,
                    int(thread_id),
                    json.dumps(member_names),
                ),
            )

        conn.commit()
        conn.close()

    def save_run(self, timestamp, guild_id, users, groups, naughty_list, db_path=None) -> None:
        self.save_signups_to_db(timestamp, guild_id, users, naughty_list, db_path=db_path)
        self.save_groups_to_db(timestamp, guild_id, groups, db_path=db_path)


class TestDataManager:
    """Drop-in replacement for DataManager that writes state to a text file."""

    def __init__(self, db_path=None) -> None:
        self.db_path = Path(db_path) if db_path else None

    def set_db_path(self, db_path) -> None:
        self.db_path = Path(db_path) if db_path else None

    def init_database(self, db_path=None) -> Path:
        target_path = Path(db_path) if db_path else self.db_path
        if not target_path:
            raise ValueError("A storage path is required")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        if not target_path.exists():
            self._write_state(target_path, {"signups": {}, "groups": {}})
        else:
            # Ensure existing files are valid JSON state.
            self._load_state(target_path)

        return target_path

    def get_db_connection(self, db_path=None):
        raise NotImplementedError("TestDataManager does not support direct DB connections")

    def _load_state(self, target_path: Path) -> dict:
        with target_path.open("r", encoding="utf-8") as handle:
            content = handle.read().strip()

        if not content:
            return {"signups": {}, "groups": {}}

        state = json.loads(content)
        if "signups" not in state:
            state["signups"] = {}
        if "groups" not in state:
            state["groups"] = {}
        return state

    def _write_state(self, target_path: Path, state: dict) -> None:
        with target_path.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)

    def _serialize_user(self, user) -> dict:
        if isinstance(user, dict):
            return {
                "timestamp": user.get("timestamp"),
                "name": user.get("name", ""),
                "words_writing": user.get("words_wr", 0),
                "words_reading": user.get("words_r", 0),
                "genres_writing": user.get("genre_wr", []),
                "genres_reading": user.get("genre_r", []),
                "cw_writing": user.get("cw_wr", []),
                "cw_veto": user.get("cw_veto", []),
                "size_preference": user.get("size_pref", []),
                "match_request": user.get("match_pref", "") or "",
                "match_veto": user.get("match_veto", "") or "",
                "prev_month_status": user.get("prev_month", ""),
                "prev_group_name": user.get("prev_group", ""),
                "crit_history": 0,
                "completed_book": 0,
                "quiz_passed": 1,
                "chapter_links": None,
            }

        return {
            "timestamp": getattr(user, "timestamp", None),
            "name": getattr(user, "name", ""),
            "words_writing": getattr(user, "words_wr", 0),
            "words_reading": getattr(user, "words_r", 0),
            "genres_writing": getattr(user, "genre_wr", []),
            "genres_reading": getattr(user, "genre_r", []),
            "cw_writing": getattr(user, "cw_wr", []),
            "cw_veto": getattr(user, "cw_veto", []),
            "size_preference": getattr(user, "size_pref", []),
            "match_request": getattr(user, "match_pref", "") or "",
            "match_veto": getattr(user, "match_veto", "") or "",
            "prev_month_status": getattr(user, "prev_month", ""),
            "prev_group_name": getattr(user, "prev_group", ""),
            "crit_history": 0,
            "completed_book": 0,
            "quiz_passed": 1,
            "chapter_links": None,
        }

    def _serialize_group(self, group) -> dict:
        if isinstance(group, dict):
            mascot = group.get("name", "")
            members = group.get("members", [])
            thread_id = group.get("thread_id", 0)
        else:
            mascot = getattr(group, "name", "")
            members = getattr(group, "members", [])
            thread_id = getattr(group, "thread_id", 0)

        member_names = []
        for member in members:
            if isinstance(member, dict):
                member_names.append(member.get("name", ""))
            else:
                member_names.append(getattr(member, "name", ""))

        return {
            "mascot": mascot,
            "thread_id": int(thread_id),
            "member_ids": member_names,
        }

    def save_signups_to_db(self, timestamp, guild_id, users, naughty_list, db_path=None) -> None:
        target_path = self.init_database(db_path)
        state = self._load_state(target_path)

        for user in users:
            serialized_user = self._serialize_user(user)
            row_timestamp = serialized_user.get("timestamp", timestamp)
            if row_timestamp is None:
                raise ValueError("Each signup row requires a timestamp from the CSV")
            name = serialized_user.get("name", "")
            key = f"{row_timestamp}:{guild_id}:{name}"
            state["signups"][key] = serialized_user

        self._write_state(target_path, state)

    def save_groups_to_db(self, timestamp, guild_id, groups, db_path=None) -> None:
        target_path = self.init_database(db_path)
        state = self._load_state(target_path)

        for group in groups:
            serialized = self._serialize_group(group)
            mascot = serialized["mascot"]
            key = f"{timestamp}:{guild_id}:{mascot}"
            state["groups"][key] = serialized

        self._write_state(target_path, state)

    def save_run(self, timestamp, guild_id, users, groups, naughty_list, db_path=None) -> None:
        self.save_signups_to_db(timestamp, guild_id, users, naughty_list, db_path=db_path)
        self.save_groups_to_db(timestamp, guild_id, groups, db_path=db_path)