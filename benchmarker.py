import time

from socket import *


def benchmark(address, number_of_messages):
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect(address)
    start = time.time()
    for n in range(number_of_messages):
        sock.send(b'x')
        sock.recv(10000)
    end = time.time()
    print(number_of_messages/(end - start), 'msgs/s')


benchmark(('localhost', 14000), 100000)
