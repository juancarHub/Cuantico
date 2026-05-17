import queue

_events = queue.Queue()


def publish(event_name: str):
    _events.put(event_name)


def wait_for(event_name: str):
    while True:
        event = _events.get()
        if event == event_name:
            return
