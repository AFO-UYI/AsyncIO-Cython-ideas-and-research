import asyncio
import websockets
import orjson

from random import random, choice
from threading import Thread
from time import sleep


loop = asyncio.get_event_loop()

clients_holder = {}

cache = {}


class Client:
    def __init__(self, websocket):
        self.ws = websocket
        self.topics = set()


async def recos_notifier(websocket, _):
    client = register_client(websocket)
    await notify_cached_info(client)
    await listen(client)


def register_client(websocket):
    client = Client(websocket)
    print('guardado un cliente en la lista')
    return client


async def notify_cached_info(client):
    msg = {}
    for topic in client.topics:
        msg.update({topic: cache[topic]})

    await client.ws.send(orjson.dumps(msg).decode('utf-8'))


async def listen(client):
    async for command in client.ws:
        op, portfolio_ids = command.split(' ', 1)
        portfolio_ids = portfolio_ids.split(' ')
        commands_domain[op](client, portfolio_ids)
        await notify_cached_info(client)


def unset_topic(client, topics):
    for topic in topics:
        client.topics.remove(topic)
        clients_holder[topic].remove(client)
        if not clients_holder[topic]:
            del clients_holder[topic]


def set_topic(client, topics):
    for topic in topics:
        client.topics.add(topic)
        clients_holder.setdefault(topic, set()).add(client)


commands_domain = {'UNSET': unset_topic,
                   'SET': set_topic}


def process_new_info(info):
    cache.setdefault(info['portfolio']['id'], {}).setdefault(info['reco']['id'], {}).update(info['reco'])
    loop.create_task(notify_new_info(info))


async def notify_new_info(info):
    clients_to_notify = clients_holder.get(info['portfolio']['id'], set())

    msg = orjson.dumps({info['portfolio']['id']:
                        {info['reco']['id']: {'id': info['reco']['id'],
                                              'assets': info['reco']['assets']}}}).decode('utf-8')
    print(msg)

    for client in clients_to_notify:
        try:
            await client.ws.send(msg)
        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK) as e:
            await client.ws.close()
            clients_holder[client.topics].remove(client)
            error_notifier(e)


portfolios_list = [
    {'portfolio': {
        'id': '1',
        'is_internal': True}},
    {'portfolio': {
        'id': '2',
        'is_internal': True}},
    {'portfolio': {
        'id': '3',
        'is_internal': False}},
    {'portfolio': {
        'id': '4',
        'is_internal': False}}
]


def reco_id_generator():
    count = 0
    while True:
        count += 1
        yield str(count)


reco_id = reco_id_generator()


def push_recos_notifications():
    while True:
        sleep(random()*3)

        notification = choice(portfolios_list).copy()
        notification.update({'reco': {'id': next(reco_id),
                                      'assets': random()}})

        if not stop_signal.done():
            loop.call_soon_threadsafe(process_new_info, notification)
        else:
            break


stop_signal = asyncio.Future()


async def run_websocket_server():
    async with websockets.serve(recos_notifier, "localhost", 8765):
        await stop_signal

        for _, clients in clients_holder.items():
            for client in clients:
                print(client)
                await client.ws.send('deploying')
                await client.ws.close()

    print('todos los clientes avisados de que se va a desplegar una nueva version.')


error_queue = asyncio.queues.Queue()


async def error_capturer():
    while not stop_signal.done() and error_queue:
        error = await error_queue.get()

        if not error:
            continue

        print('ERROR:', error)
    print('terminada la ejecucion, saliendo del bucle')


def error_notifier(error):
    loop.create_task(error_queue.put(error))


async def shutdown(tasks):
    stop_signal.set_result(True)
    error_notifier(None)
    await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)


def main():
    try:
        recos_producer = Thread(target=push_recos_notifications)
        recos_producer.start()
        ws_server = loop.create_task(run_websocket_server())
        error_handler = loop.create_task(error_capturer())
        loop.run_forever()
    except KeyboardInterrupt:
        # https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.add_signal_handler
        # https://docs.python.org/3/library/asyncio-eventloop.html#set-signal-handlers-for-sigint-and-sigterm
        # https://www.youtube.com/watch?v=bckD_GK80oY
        loop.run_until_complete(shutdown([ws_server, error_handler]))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.stop()
        loop.close()
        print('servicio cerrado')


main()
