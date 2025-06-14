
import threading
import time

from tplpy import *

def long_task():
    # Create a task that completes after 10 seconds.
    # TODO change to Task.delay
    source = TaskCompletionSource()
    def _thread():
        time.sleep(10)
        source.set_result(None)
    threading.Thread(target=_thread).start()
    return source.task

@Task
async def example():
    print("Example Begin")
    await long_task()
    print("Example End")
    return "example"

task = example()
print("Task Returned")
print(f"Result: {task.result}")
