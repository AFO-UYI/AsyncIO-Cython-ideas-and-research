from types import coroutine
from collections import deque
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE


@coroutine
def read_wait(sock):
    yield 'read_wait', sock


@coroutine
def write_wait(sock):
    yield 'write_wait', sock


def get_event_loop():
    return Loop()


class Loop:
    def __init__(self):
        self.ready_tasks = deque()
        self.selector = DefaultSelector()

    async def sock_recv(self, sock, bandwith):
        await read_wait(sock)
        return sock.recv(bandwith)

    async def sock_accept(self, sock):
        await read_wait(sock)
        return sock.accept()

    async def sock_sendall(self, sock, msg):
        while msg:
            try:
                msg_sended = sock.send(msg)
                msg = msg[msg_sended:]
            except BlockingIOError:
                await write_wait(sock)

    def create_task(self, coro):
        self.ready_tasks.append(coro)

    def run_forever(self):
        while True:

            while not self.ready_tasks:
                events = self.selector.select()
                for key, _ in events:
                    self.ready_tasks.append(key.data)
                    self.selector.unregister(key.fileobj)

            while self.ready_tasks:
                current_task = self.ready_tasks.popleft()
                try:
                    op, *args = current_task.send(None)
                    getattr(self, op)(current_task, *args)
                except StopIteration:
                    pass

    def read_wait(self, task, sock):
        self.selector.register(sock, EVENT_READ, task)

    def write_wait(self, task, sock):
        self.selector.register(sock, EVENT_WRITE, task)
