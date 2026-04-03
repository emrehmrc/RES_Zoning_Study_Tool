import os
import copy
import json
import shutil
import threading
import pandas as pd
from pathlib import Path


class SessionManager:
    """
    Thread-safe per-session state management.
    Small state lives in memory AND is persisted to a JSON file so it
    survives Django dev-server auto-reloads.
    Large DataFrames are pickled to disk separately.
    """

    _lock = threading.Lock()
    _sessions: dict = {}
    STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / 'temp' / 'sessions'

    _DEFAULT_SESSION = {
        'project_type': None,
        'grid_created': False,
        'scoring_complete': False,
        'layer_configs': [],
        'scoring_rules': None,
        'financial_constants': None,
        'cp_values': None,
    }

    # Keys that are safe to JSON-serialize and persist between restarts.
    _PERSIST_KEYS = frozenset(_DEFAULT_SESSION.keys())

    @classmethod
    def _ensure_dir(cls, session_id: str) -> Path:
        d = cls.STORAGE_DIR / session_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    @classmethod
    def _meta_file(cls, session_id: str) -> Path:
        return cls.STORAGE_DIR / session_id / 'session_meta.json'

    @classmethod
    def _save_to_disk(cls, session_id: str):
        """Persist the current in-memory session metadata to JSON (best-effort)."""
        try:
            d = cls._ensure_dir(session_id)
            data = {k: cls._sessions[session_id][k]
                    for k in cls._PERSIST_KEYS
                    if k in cls._sessions[session_id]}
            with open(d / 'session_meta.json', 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception:
            pass  # never crash on disk write failure

    @classmethod
    def _load_from_disk(cls, session_id: str) -> dict | None:
        """Try to restore session metadata from disk (used after server restart)."""
        try:
            path = cls._meta_file(session_id)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                session = copy.deepcopy(cls._DEFAULT_SESSION)
                session.update({k: v for k, v in data.items() if k in cls._PERSIST_KEYS})
                return session
        except Exception:
            pass
        return None

    @classmethod
    def get_session(cls, session_id: str) -> dict:
        with cls._lock:
            if session_id not in cls._sessions:
                # Try to restore from disk first (survives server restarts)
                restored = cls._load_from_disk(session_id)
                cls._sessions[session_id] = restored if restored is not None else copy.deepcopy(cls._DEFAULT_SESSION)
            return copy.deepcopy(cls._sessions[session_id])

    @classmethod
    def update_session(cls, session_id: str, **kwargs):
        with cls._lock:
            if session_id not in cls._sessions:
                restored = cls._load_from_disk(session_id)
                cls._sessions[session_id] = restored if restored is not None else copy.deepcopy(cls._DEFAULT_SESSION)
            cls._sessions[session_id].update(kwargs)
            cls._save_to_disk(session_id)

    @classmethod
    def save_dataframe(cls, session_id: str, name: str, df):
        d = cls._ensure_dir(session_id)
        df.to_pickle(str(d / f'{name}.pkl'))

    @classmethod
    def load_dataframe(cls, session_id: str, name: str):
        d = cls._ensure_dir(session_id)
        path = d / f'{name}.pkl'
        if path.exists():
            return pd.read_pickle(str(path))
        return None

    @classmethod
    def has_dataframe(cls, session_id: str, name: str) -> bool:
        d = cls.STORAGE_DIR / session_id
        return (d / f'{name}.pkl').exists()

    @classmethod
    def reset_session(cls, session_id: str):
        with cls._lock:
            cls._sessions[session_id] = copy.deepcopy(cls._DEFAULT_SESSION)
        d = cls.STORAGE_DIR / session_id
        if d.exists():
            # Explicitly unlink individual pkl files first (avoids Windows file-lock issues)
            for pkl in d.glob('*.pkl'):
                try:
                    pkl.unlink(missing_ok=True)
                except OSError:
                    pass
            # Remove the JSON metadata file too
            try:
                (d / 'session_meta.json').unlink(missing_ok=True)
            except OSError:
                pass
            # Then remove the directory (best-effort)
            shutil.rmtree(str(d), ignore_errors=True)
