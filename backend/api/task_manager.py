"""
Thread-based task runner with progress tracking.
Allows long-running operations (analysis, scoring, clustering) to run
in background threads while the frontend polls for progress.
"""
import threading
import traceback
import uuid
from datetime import datetime

_tasks: dict = {}
_lock = threading.Lock()


def create_task(func, *args, **kwargs):
    """Start *func* in a daemon thread and return a task_id for polling."""
    task_id = uuid.uuid4().hex[:10]
    with _lock:
        _tasks[task_id] = {
            'status': 'running',
            'progress': 0,
            'message': 'Starting...',
            'steps': [],
            'result': None,
            'error': None,
            'started_at': datetime.now().isoformat(),
        }

    def _update(progress: int, message: str):
        with _lock:
            t = _tasks.get(task_id)
            if t:
                t['progress'] = progress
                t['message'] = message
                t['steps'].append(message)

    def _wrapper():
        try:
            result = func(*args, progress_callback=_update, **kwargs)
            with _lock:
                t = _tasks[task_id]
                t['status'] = 'completed'
                t['progress'] = 100
                t['message'] = 'Complete'
                t['result'] = result
        except Exception as e:
            with _lock:
                t = _tasks[task_id]
                t['status'] = 'failed'
                t['error'] = str(e)
                t['traceback'] = traceback.format_exc()

    thread = threading.Thread(target=_wrapper, daemon=True)
    thread.start()
    return task_id


def get_task(task_id: str) -> dict | None:
    with _lock:
        t = _tasks.get(task_id)
        return dict(t) if t else None


def cleanup_task(task_id: str):
    with _lock:
        _tasks.pop(task_id, None)
