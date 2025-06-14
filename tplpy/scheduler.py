from concurrent.futures import ThreadPoolExecutor

class TaskScheduler:

    default_scheduler = None

    @staticmethod
    def default():
        return TaskScheduler.default_scheduler

    @staticmethod
    def set_default(scheduler):
        TaskScheduler.default_scheduler = scheduler

    def post(self, func, *args, **kwargs):
        raise NotImplementedError

class ThreadPoolScheduler(TaskScheduler):

    def __init__(self):
        self._pool = ThreadPoolExecutor()

    def post(self, func, *args, **kwargs):
        self._pool.submit(func, *args, **kwargs)

TaskScheduler.set_default(ThreadPoolScheduler())
