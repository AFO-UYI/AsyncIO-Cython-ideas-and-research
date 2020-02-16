import asyncio
import websockets
import orjson

from random import random, choice
from threading import Thread
from time import sleep


loop = asyncio.get_event_loop()

protected_client_holder = {'all', 'internas', 'externas'}
clients_holder = {'internas': set(),
                  'externas': set(),
                  'all': set()}

cache = {}
cached_internal_ids = set()


class Client:
    def __init__(self, websocket):
        self.ws = websocket
        self.topic = None


async def recos_notifier(websocket, _):
    initial_topic = await websocket.recv()
    client = register_client(websocket, initial_topic)
    await notify_cached_info(client)
    await listen(client)


def register_client(websocket, initial_topic):
    client = Client(websocket)

    set_topic(client, initial_topic)

    print('guardado un cliente en la lista')
    print(clients_holder)

    return client


async def notify_cached_info(client):
    if client.topic == 'all':
        msg = cache
    elif client.topic == 'internas':
        msg = {key: value for key, value in cache.items() if key in cached_internal_ids}
    elif client.topic == 'externas':
        msg = {key: value for key, value in cache.items() if key not in cached_internal_ids}
    else:
        msg = {client.topic: cache[client.topic]}

    await client.ws.send(orjson.dumps(msg).decode('utf-8'))


async def listen(client):
    async for topic in client.ws:
        update_topic(client, topic)
        await notify_cached_info(client)


def update_topic(client, topic):
    clients_holder[client.topic].remove(client)
    if not clients_holder[client.topic] and client.topic not in protected_client_holder:
        del clients_holder[client.topic]

    set_topic(client, topic)


def set_topic(client, topic):
    client.topic = topic
    clients_holder.setdefault(topic, set()).add(client)


def process_new_info(info):
    cache.setdefault(info['portfolio']['id'], {}).setdefault(info['reco']['id'], {}).update(info['reco'])

    if info['portfolio']['is_internal']:
        cached_internal_ids.add(info['portfolio']['id'])

    loop.create_task(notify_new_info(info))


async def notify_new_info(info):
    clients_to_notify = clients_holder['all'].union(
        clients_holder['internas'] if info['portfolio']['is_internal'] else clients_holder['externas'],
        clients_holder.get(info['portfolio']['id'], set()))
    msg = orjson.dumps({info['portfolio']['id']:
                        {info['reco']['id']: {'id': info['reco']['id'],
                                              'assets': info['reco']['assets']}}}).decode('utf-8')
    print(msg)

    for client in clients_to_notify:
        try:
            await client.ws.send(msg)
        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
            await client.ws.close()
            clients_holder[client.topic].remove(client)


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

        loop.call_soon_threadsafe(process_new_info, notification)


Thread(target=push_recos_notifications).start()


loop.run_until_complete(websockets.serve(recos_notifier, "localhost", 8765))
loop.run_forever()
