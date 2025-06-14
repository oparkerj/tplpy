import threading

class TaskSyncContext:

    local = threading.local()

    @staticmethod
    def current():
        return TaskSyncContext.local.__dict__.get("context")

    @staticmethod
    def set_context(context):
        TaskSyncContext.local.context = context

    def post(self, func, *args, **kwargs):
        raise NotImplementedError
