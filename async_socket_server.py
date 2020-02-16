import azincioh as asincronia

from socket import *

loop = asincronia.get_event_loop()


async def socket_server(address):
    sock = socket(AF_INET, SOCK_STREAM)
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)
    sock.bind(address)
    sock.listen(5)
    sock.setblocking(False)

    while True:
        client, addr = await loop.sock_accept(sock)
        loop.create_task(server_echo(client, addr))


async def server_echo(client, addr):
    print(f'conexion con {addr}')
    with client:
        while True:
            msg = await loop.sock_recv(client, 10000)
            print(msg)
            if not msg:
                break
            await loop.sock_sendall(client, msg)
        print(f'conexion cerrada con {addr}')


loop.create_task(socket_server(('localhost', 14000)))
loop.run_forever()
