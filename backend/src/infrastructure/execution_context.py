import threading
import asyncio
from contextvars import ContextVar
from typing import Optional, Tuple

# ContextVars are used for async execution paths; thread-local is used for
# synchronous code executed in worker threads. Getters prefer ContextVar when
# available, falling back to thread-local storage.
_session_var: ContextVar[Optional[object]] = ContextVar('_session_var', default=None)
_request_id_var: ContextVar[Optional[str]] = ContextVar('_request_id_var', default=None)

_thread_local = threading.local()

# Registry for outstanding requests so callers (e.g. cancel endpoint)
# can attempt to cancel running tasks or signal thread-based workers to stop.
_registry_lock = threading.Lock()
_registry = {}  # request_id -> { 'task': asyncio.Task | None, 'event': threading.Event }

def register_task(request_id: str, task) -> None:
    with _registry_lock:
        entry = _registry.get(request_id)
        if not entry:
            entry = {'task': None, 'event': threading.Event()}
            _registry[request_id] = entry
        entry['task'] = task

def unregister_task(request_id: str) -> None:
    with _registry_lock:
        if request_id in _registry:
            try:
                del _registry[request_id]
            except Exception:
                pass

def set_cancel(request_id: str) -> None:
    with _registry_lock:
        entry = _registry.get(request_id)
        if not entry:
            # create a placeholder so future checks for cancellation will see it
            entry = {'task': None, 'event': threading.Event()}
            _registry[request_id] = entry
        try:
            entry['event'].set()
            if entry.get('task') is not None:
                try:
                    entry['task'].cancel()
                except Exception:
                    pass
        except Exception:
            pass

def is_cancelled_current() -> bool:
    session, reqid = get_current()
    if not reqid:
        return False
    with _registry_lock:
        entry = _registry.get(reqid)
        if not entry:
            return False
        return bool(entry['event'].is_set())

def get_cancel_event_for_request(request_id: str):
    with _registry_lock:
        entry = _registry.get(request_id)
        if not entry:
            entry = {'task': None, 'event': threading.Event()}
            _registry[request_id] = entry
        return entry['event']


def set_for_context(session: object, request_id: str) -> Tuple[ContextVar, ContextVar]:
    """Set session/request_id for current async context. Returns tokens for reset."""
    token_s = _session_var.set(session)
    token_r = _request_id_var.set(request_id)
    return (token_s, token_r)


def reset_context(tokens: Tuple[ContextVar, ContextVar]) -> None:
    """Reset previously set ContextVar tokens."""
    try:
        _session_var.reset(tokens[0])
        _request_id_var.reset(tokens[1])
    except Exception:
        # ignore invalid resets
        pass


def set_for_thread(session: object, request_id: str) -> None:
    _thread_local.session = session
    _thread_local.request_id = request_id


def clear_for_thread() -> None:
    for attr in ('session', 'request_id'):
        if hasattr(_thread_local, attr):
            try:
                delattr(_thread_local, attr)
            except Exception:
                pass


def get_current() -> Tuple[Optional[object], Optional[str]]:
    """Return (session, request_id) for current execution context.
    Prefers ContextVar for async paths, falls back to thread-local for worker threads.
    """
    session = _session_var.get()
    if session is not None:
        return session, _request_id_var.get()
    session = getattr(_thread_local, 'session', None)
    request_id = getattr(_thread_local, 'request_id', None)
    return session, request_id
