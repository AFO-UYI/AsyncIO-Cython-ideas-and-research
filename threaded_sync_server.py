from socket import *
from threading import Thread


def socket_server(address):
    sock = socket(AF_INET, SOCK_STREAM)
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)
    sock.bind(address)
    sock.listen(5)

    while True:
        client, addr = sock.accept()
        Thread(target=server_echo, args=(client, addr)).start()


def server_echo(client, addr):
    print(f'conexion con {addr}')
    with client:
        while True:
            msg = client.recv(10000)
            if not msg:
                break
            client.send(msg)
        print(f'conexion cerrada con {addr}')


socket_server(('localhost', 14000))
