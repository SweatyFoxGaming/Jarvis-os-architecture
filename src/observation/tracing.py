from contextvars import ContextVar
from .events import new_trace

_current_trace = ContextVar("trace", default=None)


def begin_trace():

    trace = new_trace()

    _current_trace.set(trace)

    return trace


def current_trace():

    return _current_trace.get()


def end_trace():

    _current_trace.set(None)
