import inspect
import threading

from . import context as _context
from . import scheduler as _scheduler
from . import wrapper as _wrapper

class TaskState:

    NEW = 0
    RUNNING = 1
    SUCCEEDED = 2
    FAULTED = 3
    CANCELLED = 4

class Task:

    def __new__(cls, func):
        if func is None:
            return super().__new__(cls)
        if inspect.iscoroutinefunction(func) or inspect.isgeneratorfunction(func):
            return _wrapper._task_coroutine_wrapper(func)
        if callable(func):
            return _wrapper._task_sync_wrapper(func)
        raise ValueError

    def __init__(self, unused):
        self._condition = threading.Condition()
        self._state = TaskState.NEW
        self._continuations = []
        self._value = None

    def __await__(self):
        return (yield self)

    def _is_running_unsafe(self):
        return self._state == TaskState.RUNNING

    def _is_completed_unsafe(self):
        return self._state != TaskState.RUNNING

    def _is_succeeded_unsafe(self):
        return self._state == TaskState.SUCCEEDED

    def is_running(self):
        with self._condition:
            return self._is_running_unsafe()

    def is_completed(self):
        with self._condition:
            return self._is_completed_unsafe()

    def is_succeeded(self):
        with self._condition:
            return self._is_succeeded_unsafe()

    def is_faulted(self):
        with self._condition:
            return self._state == TaskState.FAULTED

    def is_cancelled(self):
        with self._condition:
            return self._state == TaskState.CANCELLED

    @property
    def running(self):
        return self.is_running()

    @property
    def completed(self):
        return self.is_completed()

    @property
    def succeeded(self):
        return self.is_succeeded()

    @property
    def faulted(self):
        return self.is_faulted()

    @property
    def cancelled(self):
        return self.is_cancelled()

    def _get_result_internal(self):
        if self._is_succeeded_unsafe():
            return self._value
        if self._state in (TaskState.FAULTED, TaskState.CANCELLED):
            raise self._value
        raise RuntimeError("Invalid task state.")

    def get_result(self, timeout=None):
        with self._condition:
            if self._is_completed_unsafe():
                return self._get_result_internal()

            if not self._condition.wait(timeout=timeout):
                raise TaskTimeout

            return self._get_result_internal()

    @property
    def result(self):
        return self.get_result()

    def configure_await(self, capture_context):
        return ConfiguredTaskAwaitable(self, capture_context)

    def continue_with(self, callback):
        # TODO this should return a Task
        with self._condition:
            if not self._is_completed_unsafe():
                self._continuations.append(callback)
                return
        callback(self)

    def _run_continuations(self):
        for continuation in self._continuations:
            try:
                continuation(self)
            except Exception:
                pass
        self._continuations = None

    def _try_set_state(self, value, state):
        with self._condition:
            if self._is_completed_unsafe():
                return False
            self._value = value
            self._state = state
            self._condition.notify_all()
        self._run_continuations()
        return True

    def _set_state(self, value, state):
        if not self._try_set_state(value, state):
            raise RuntimeError("Invalid task state.")

    def _set_running(self):
        with self._condition:
            if self._state == TaskState.NEW:
                self._state = TaskState.RUNNING
            else:
                raise RuntimeError("Task is not new.")

    def _set_result(self, value):
        self._set_state(value, TaskState.SUCCEEDED)

    def _set_exception(self, exception):
        self._set_state(exception, TaskState.FAULTED)

    def _set_cancelled(self, cancel_token=None):
        self._set_state(TaskCancel(cancel_token), TaskState.CANCELLED)

    def _try_set_result(self, value):
        return self._try_set_state(value, TaskState.SUCCEEDED)

    def _try_set_exception(self, exception):
        return self._try_set_state(exception, TaskState.FAULTED)

    def _try_set_cancelled(self, cancel_token=None):
        return self._try_set_state(TaskCancel(cancel_token), TaskState.CANCELLED)

    def _exec_coroutine(self, func, *args, **kwargs):
        self._set_running()
        coro = func(*args, **kwargs)
        self._continue_coroutine(coro, None, True)

    def _continue_coroutine(self, coro, value, send):
        while True:
            try:
                task = coro.send(value) if send else coro.throw(value)
                capture = True
                if isinstance(task, ConfiguredTaskAwaitable):
                    capture, task = task.capture_context, task.task

                if task.completed:
                    value, send = task._value, task._is_succeeded_unsafe()
                    continue
                else:
                    context = _context.TaskSyncContext.current() if capture else None
                    if context is None:
                        context = _scheduler.TaskScheduler.default()
                    task.continue_with(
                        lambda t: context.post(self._continue_coroutine, coro, t._value, t._is_succeeded_unsafe()))
            except StopIteration as e:
                coro.close()
                self._set_result(e.value)
            except TaskCancel as e:
                coro.close()
                self._set_cancelled(e.cancel_token)
            except Exception as e:
                # TODO should this be BaseException
                coro.close()
                self._set_exception(e)
            return

    def _exec_sync(self, func, *args, **kwargs):
        self._set_running()
        try:
            self._set_result(func(*args, **kwargs))
        except TaskCancel as e:
            self._set_cancelled(e.cancel_token)
        except Exception as e:
            # TODO should this be BaseException
            self._set_exception(e)

class ConfiguredTaskAwaitable:

    def __init__(self, task, capture_context):
        self.task = task
        self.capture_context = capture_context

    def __await__(self):
        return (yield self)

class TaskTimeout(Exception):
    pass

class TaskCancel(Exception):

    def __init__(self, cancel_token=None):
        self.cancel_token = cancel_token
