import functools

from . import task as _task

def _task_coroutine_wrapper(func):
    @functools.wraps(func)
    def _exec(*args, **kwargs):
        task = _task.Task(None)
        task._exec_coroutine(func, *args, **kwargs)
        return task
    return _exec

def _task_sync_wrapper(func):
    @functools.wraps(func)
    def _exec(*args, **kwargs):
        task = _task.Task(None)
        task._exec_sync(func, *args, **kwargs)
        return task
    return _exec
