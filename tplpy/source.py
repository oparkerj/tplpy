from . import task as t_task

class TaskCompletionSource:

    def __init__(self):
        self._task = t_task.Task(None)

    @property
    def task(self):
        return self._task

    def set_result(self, value):
        self._task._set_result(value)

    def set_exception(self, exception):
        self._task._set_exception(exception)

    def set_cancelled(self, cancel_token=None):
        self._task._set_cancelled(cancel_token)

    def try_set_result(self, value):
        return self._task._try_set_result(value)

    def try_set_exception(self, exception):
        return self._task._try_set_exception(exception)

    def try_set_cancelled(self, cancel_token=None):
        return self._task._try_set_cancelled(cancel_token)
