variable = 'ola que ase'


def funcion():
    print('chirivistro_pi')

# direcciones -> id()

##########################################################################


none_variable = None


def miss_funcion(func):
    global none_variable
    none_variable = func


@miss_funcion
def variable_call():
    print('asereje')


##########################################################################


def return_function():
    def function_returned():
        print('wea random')

    return function_returned


##########################################################################


def return_function_burned(x):
    def multiply_something(y):
        return x*y

    return multiply_something


##########################################################################


def return_function_with_closure():
    count = 0

    def counter():
        nonlocal count
        count += 1
        return count

    return counter

# __code__.co_freevars el nombre y __closure__[0].cell_contents el valor


##########################################################################


def generador():
    count = 0

    while True:
        count += 1
        print('previo al yield')
        yield count
        print('despues del yied')


##########################################################################

array_de_pruebas = [1, 2, 3, 4, 5, 6, 7]
diccionario_de_pruebas = {'1': 2, '3': 4, '5': 6}
set_de_pruebas = {1, 2, 3, 4, 5, 6, 7}
tupla_de_pruebas = (1, 2, 3, 4, 5, 6, 7)

list_comp = [x for x in array_de_pruebas]
dict_comp = {key: value for key, value in diccionario_de_pruebas.items()}
set_comp = {x for x in set_de_pruebas}
algo_comp = (x for x in tupla_de_pruebas)


##########################################################################


def generador_finito():
    count = 0

    while count < 5:
        count += 1
        print('previo al yield')
        yield count
        print('despues del yied')


##########################################################################


def generador_finito_con_mensaje():
    count = 0

    while count < 5:
        count += 1
        print('previo al yield')
        yield count
        print('despues del yied')

    return 'termine la iteracion'


##########################################################################


def generador_con_escritura():
    count = 0

    while count < 5:
        count += 1
        print('previo al yield')
        variable_de_escritura = yield count
        print(variable_de_escritura)
        print('despues del yied')


##########################################################################

def yield_function():
    count = yield
    count = yield count
    yield count


##########################################################################


def yield_from_gather_function():
    yield from "abc"
    yield from [1, 2]
    print(variable)
    return "gather finished"


##########################################################################
from types import coroutine

@coroutine
def funcion_corrutina(x):
    print(f'en la corrutina {x}')
    yield f'en el yield de la corrutina {x}'


async def funcion_asincrona():
    count = 0
    while count < 5:
        count += 1
        print(count)
        print('antes del await')
        variable = await funcion_corrutina(count)
        print(f'variable: {variable}')


##########################################################################
from types import coroutine

@coroutine
def funcion_corrutina_2(x):
    print(f'en la corrutina {x}')
    yield f'en el yield de la corrutina {x}'
    yield f'en el segundo yield de la corrutina {x}'
    return 'ola que ase'


async def funcion_asincrona_2():
    count = 0
    while count < 5:
        count += 1
        print(count)
        print('antes del await')
        variable = await funcion_corrutina_2(count)
        print(f'variable: {variable}')


##########################################################################
from types import coroutine

@coroutine
def funcion_corrutina_3(x):
    print(f'en la corrutina {x}')
    yield f'en el yield de la corrutina {x}'
    variable = yield f'en el segundo yield de la corrutina {x}'
    return variable


async def funcion_asincrona_3():
    count = 0
    while count < 5:
        count += 1
        print(count)
        print('antes del await')
        variable = await funcion_corrutina_3(count)
        print(f'variable: {variable}')


##########################################################################
def function_one():
    print('soy la funcion 1')


def function_two():
    print('soy la funcion 2')


def function_three():
    print('soy la funcion 3')


def function_four():
    print('soy la funcion 4')


def yield_functions():
    list_of_functions = [function_one, function_two, function_three, function_four]
    for function in list_of_functions:
        yield function


##########################################################################
##########################################################################
# asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# https://www.techempower.com/benchmarks/#section=test&runid=7464e520-0dc2-473d-bd34-dbdfd7e85911&hw=ph&test=query&l=zijzen-7
# http://magic.io/blog/uvloop-blazing-fast-python-networking/
# https://github.com/MagicStack/asyncpg
# https://aio-pika.readthedocs.io/en/latest/



