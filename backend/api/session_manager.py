import os
import shutil
import threading
import pandas as pd
from pathlib import Path


class SessionManager:
    """
    Thread-safe per-session state management.
    Small state lives in memory; large DataFrames are pickled to disk.
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

    @classmethod
    def _ensure_dir(cls, session_id: str) -> Path:
        d = cls.STORAGE_DIR / session_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    @classmethod
    def get_session(cls, session_id: str) -> dict:
        with cls._lock:
            if session_id not in cls._sessions:
                cls._sessions[session_id] = dict(cls._DEFAULT_SESSION)
            return dict(cls._sessions[session_id])

    @classmethod
    def update_session(cls, session_id: str, **kwargs):
        with cls._lock:
            if session_id not in cls._sessions:
                cls._sessions[session_id] = dict(cls._DEFAULT_SESSION)
            cls._sessions[session_id].update(kwargs)

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
            cls._sessions[session_id] = dict(cls._DEFAULT_SESSION)
        d = cls.STORAGE_DIR / session_id
        if d.exists():
            shutil.rmtree(str(d), ignore_errors=True)
