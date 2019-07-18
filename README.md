# AsyncIO + Cython (context, ideas and research)

Dealing with AsyncIO on a personal proyect, some needs were raised that AsyncIO aparrently doesnt resolve. After a while, I'm diving increasingly deep about how asynchronous code works in python and whats the point with AsyncIO. Here are some notes about what I learn.

1. Understanding how asynchronous code works.
   * Pointers and First Class Functions.
   * Function contexts and closures.
   * Yield, StopIteration error and Yield From.
   * Async/Await.
   * Queues.
   * Selector.
   * Finally, how asynchronous code works.
2. AsyncIO.
   * Multithreading vs GIL.
   * AsyncIO module.
3. Async multithreading?
   * An Asynchronous purpose twist.
   * Tasks Schedulers, IPC problems and Compute Express Link.
4. AsyncIO difficulties and Cython possibilities.

----

# 1. Understanding how asynchronous code works.

There are a few steps in Python and programming history to understand how the asynchronous idea arrived.

## 1.1. Pointers and First Class Functions.

First of all, I need to explain something so badly expressed along a lot of sites. Variables are not values, are memory address.

If you have in python something like `a = 10`, `a` is not 10, is the memory address where 10 is saved. In memory you can have values or instructions, and you have names where is hold those value's and instruction's memory address. So, really you can think about functions like a data type which can be called to preform something instead of just be a value.

For that reason you have those lambda functions (or anon functions) being stored on a "variable". Eg: 

```python
a_sum = lambda x, y: x+y

print(a_sum(3, 4)) # prints 7
```

This really do the same as ussual `def` definitions in python, and can be considered a syntactic sugar. Indeed if you are in PyCharm and copypaste the code above, the ide will warn you that pep 8 is complaining because you must not assign a lambda function.

With this, I want advice that variables really are pointers. Depending if a variable points to a plain value or an instruction could be added `()` or not to that pointer name to run those instructions. In python if you use a function name without `()` will return a string with functions attributes, one of those ussually are the memory address in hexadecimal. With value pointers you cant get the memory address in that way because you will get the pinted value, but if you use `id(variable_name)` will get the memory address of that pointer in decimal. And because pointers are pointers, you also can do `id(function_name)` and you could see is the same memory address as the string printed at calling `function_name` without `()`, just one is in decimal and the other is in hexadecimal.

These pointers as iinterfaces to play with instructions and values, makes that functions in python get some special capabilities. Those functions with special capabilities are named first class functions, which can be treated as we treat with values.

## 1.2. Function contexts and closures.

In Python, one of the special capabilities of functions to be first class functions is that functions are instance of the Object type. That means, functions have some attributes stored on a dictionary where are holded things like local variables references or parameters information. Those attributes are called the context of a function and is created at defition time (when interpreter hits a `def` line).

As I said before, first class functions can be treated as we treat variables, and one of these treats is that we can declare new functions inside a function.

```python
def generator_function():

    def generated_function():
        print('Im a generated function')

    return generated_function     # we return the address, not a call ( generated_function without () )


g = generator_function()
print(g)       # prints <function generator_function.<locals>.generated_function at 0x000001BD58FE5048>
g()            # prints Im a generated function
```

When we call `g = generator_function()` interpreter hits `def generated_function`, instace an Object for `generated_function` and stores it in memory and give to `g` the memory address.

An interesting thing here is... If `generator_function` have some locals variables, for `generated_functions` those variables will be like globals. Context for `generated_functions` is created at `generator_function` call, so in `generated_function` context will be that variables in context. Those viariables ara called closures.

```python
def generator_function():

    closure_variable = 42

    def generated_function():
        print(closure_variable)

    return generated_function


g = generator_function()
print(g.__code__.co_freevars)           # prints ('closure_variable',)
print(g.__closure__[0].cell_contents)   # prints 42
g()                                     # prints 42
```

In the code above `generator_function` has a local variable named `closure_variable` and is used by `generated_function`. When interpreter hits `def generaated_function` creates an Object with attributes like `__code__.co_freevars` and `__closure__[0].cell_contents` where are stored the name and value of the closure respectively.

Even you can change the value of those closures using the `nonlocal` keyword.

```python
def generator_function():

    closure_variable = 0

    def generated_function():
        nonlocal closure_variable
        print(closure_variable)
        closure_variable += 1

    return generated_function


counter = generator_function()
counter()             # prints 0
counter()             # prints 1
counter()             # prints 2
counter()             # prints 3
```

For each counter you create with `generator_function` the counter will start at 0, because the local variable of `generator_function` is 0 and when you call it, a new Object with its own context is created. Furthermore, an usefull thing of this, is that you can do other things between calls.

```python
counter = generator_function()
counter2 = generator_function()
counter()              # prints 0
counter()              # prints 1
counter2()             # prints 0
# doing another things
counter()              # prints 2
counter2()             # prints 1
# doing another things
counter()              # prints 3
counter2()             # prints 2
```

## 1.3. Yield, StopIteration error and Yield From.

The `yield` keyword is kinda syntactic sugar to create generators like in the codes above, but adds some extra things improving usability and capabilities. To define a generator with yield:

```python
def yield_function():
    count = 0
    while True:
        yield print(count)
        count += 1

counter = yield_function()
print(counter)  # prints <generator object yield_function at 0x00000264461C2228>
next(counter)   # prints 0
next(counter)   # prints 1
next(counter)   # prints 2
```

Now, we dont need nested functions defined inside, or nonlocal variables. We just need write `yield` at some point, and call the generator object throw `next()` instead of call the generator directly adding `()`.

What iis happening really with `yield` is more interesting. `yield` stops and exits the execution of a function when interpreter hits the `yield` line, but the progress of that function is saved as a context update. So, in the first `next(counter)`, function hits `yield print(counter)`, stops and exits. Then in the next `next(counter)` count increments by 1 and again at `yield print(counter)` stops and exits, but now the context function was updated being count value equal to 1. And thats happen every `next(counter)` call. 

`yield` also have the capability to return values. So the code above could be: 
```python
def yield_function():
    count = 0
    while True:
        yield count
        count += 1

counter = yield_function()
print(next(counter))   # prints 0
print(next(counter))   # prints 1
print(next(counter))   # prints 2
```

Now the `count` value is returned and must be printed outside the function. This with the closure way must be diferent because the only way to return something is with `return` keyword, and anothers extra operations must be called mandatorily before `return`. `yield` is more comfy and adaptable to some situations.

Also, with `yield` we can send values inside the function.

```python
def yield_function():
    count = 0
    while True:
        count = yield count

counter = yield_function()
print(next(counter))      # prints 0
print(counter.send(13))   # prints 13
print(counter.send(42))   # prints 42
print(counter.send(23))   # prints 23
print(counter.send(7))    # prints 7
```

In this cases, `yield` stops the functions right at the assignment step, thats means, `count = yield` will be preformed in the next call. So, each step starts on the assignment and stops at the return of count. Thats why counter is printing the value we are sending.

`next()` really is a `counter.send(None)` both calls are the same. The first call of counter must be that because starts from the very first line of the function, and no assignment with `yield` is preformed there. The `next()` call stops right at the first assignment with `yield`.

Like with closures, other things can be preformed between `next` or `send` calls.

Far from loops. We can make yields with functions that can be finished.

```python
def yield_function():
    count = yield
    count = yield count
    yield count
    
counter = yield_function()
print(next(counter))      # prints None
print(counter.send(13))   # prints 13
print(counter.send(42))   # prints 42
print(counter.send(23))   # StopIteration error-like is raised
```

Here we can see that being `count = yield` the very first operation in the function, calling `next(counter)` we send `None` and then is returned and printed from outside the function. 

Also we can see, if we attempt to call counter 4 times, when the function have just 3 yields, a StopIteration error ir raised. StopIteration is normal and totally usefull for those generators with uncertain finishs inside loops. We must remember catch the exception and prevent our apps stop.

StopIteration also can return values within. Eg:

```python
def yield_function():
    count = yield
    count = yield count
    yield count
    return 'something after yields'

counter = yield_function()
print(next(counter))      # prints None
print(counter.send(13))   # prints 13
print(counter.send(42))   # prints 42
print(next(counter))      # raise StopIteration: something after yields
```

The returned value will be the StopIteration message. This message can be catched with:

```python
counter = yield_function()
print(next(counter))      # prints None
print(counter.send(13))   # prints 13
print(counter.send(42))   # prints 42
try:
    print(next(counter))      
except StopIteration as e:
    print(e.value)        # prints something after yields
```

In addition, we have the `yield from` keyword. A `yield from` in a function body produces a generator function aswell. But this generator yields over another generator. `yield from` automatically handles everything over the generator which is yielding, even the StopIteration. In case of some value is returned at StopIteration raising, the value will be returned in the `yield from` line. `yield form` has its own StopIteration to be controlled when the iteration is finished. Some examples:

```python
def yield_function():
    count = yield
    count = yield count
    yield count
    return 'something after yields'


def another_yield_function():
    x = yield from yield_function() # (x = 'something after yields') when yield_function raise StopIteration
    print(x)


counter = another_yield_function()
print(counter)            # prints <generator object another_yield_function at 0x0000026285250318>
print(next(counter))      # prints None
print(counter.send(13))   # prints 13
print(counter.send(42))   # prints 42
# prints something after yields from the print on another_yield_function
print(next(counter))      # raise StopIteration with no values.
```

We must catch that StopIteration of `another_yield_function` as we did before. If we want do something with the returned value by `yield_function` we just must tu return it on `another_yield_function` aswell.

```python
def another_yield_function():
    x = yield from yield_function() # (x = 'something after yields') when yield_function raise StopIteration
    return x

...

print(counter.send(42))   # prints 42
print(next(counter))      # raise StopIteration: something after yields.
```

To point is, whatever we return in a generator, will be displayed as StopIteration value.

You can see that in a macro view of the code behaviour `yield from` have the same needs and preform the same like plain `yield`. You can see `yield from` indeed like a tunnel between the outest and most internal generators. The real deal with `yield from` is the capabitily to gather various generator.

```python 
def yield_from_gaather_function():
    yield from "abc"
    yield from [1, 2]
    return "gather finished"


counter = yield_from_gaather_function()
print(next(counter))      # prints a
print(next(counter))      # prints b
print(next(counter))      # prints c
print(next(counter))      # prints 1
print(next(counter))      # prints 2
print(next(counter))      # raise StopIteration: gather finished
```

In this example also you can see `yield from` can yield over iterables. Indeed, an iterable object must has defined an `__iter__` method that return an iterator which in essence is a generator.

```python
test = "abcd"
iterator = test.__iter__()
print(iterator)          # prints <str_iterator object at 0x00000190F7B163C8>
print(next(iterator))    # prints a
print(next(iterator))    # prints b
print(next(iterator))    # prints c
print(next(iterator))    # prints d
print(next(iterator))    # raise StopIteration
```

## 1.4. Async/Await.

`Async / Await` is a specialization of a `yield` use case. In the examples above we use `yield`and `yield from` for lazy iterations. Something useful if you dont want all the list at once. But as I said before, functions in python are first class functions and can be used as a variable, so you can yield over an iterable of functions.

```python
def function_one():
    print('Im the function_one')

def function_two():
    print('Im the function_two')

def function_three():
    print('Im the function_three')

def function_four():
    print('Im the function_four')

def yield_functions():
    list_of_functions = [function_one, function_two, function_three, function_four]
    for function in list_of_functions:
        yield function

g = yield_functions()

# now we use next(g) + (), next(g) returns functions memory address
# and () runs the function on those address

next(g)()  # prints Im the function_one
next(g)()  # prints Im the function_two
next(g)()  # prints Im the function_three
next(g)()  # prints Im the function_four
next(g)()  # raise StopIteration
```

`async / await` exists for readability and optimizations. And creates a new way to think in code design. But under the hood, how it works is the same, more close to `yield from` than `yield`. Eg:

```python
from types import coroutine

@coroutine
def yield_function(number):
    print('Im the yield function')
    yield number
    print('after yield')
    return 'hello world'

async def async_function():
    print('first print')
    value = await yield_function(3)
    print('the return of await is: ', value)
    await yield_function(5)
    return 'end of async'

coro = async_function()

print(coro)            # prints <coroutine object async_function at 0x000002AE753F25C8>
                       # Is a Coroutine object, not a generator.

print(coro.send(None)) # prints first print (first line of async_function)
                       #        Im the yield function (first line of yield_function)
                       #        3 ( print(coro.send(None)) by itself )
                                
print('send')          # prints send

print(coro.send(None)) # prints after yield (third line of yield_function)
                       #        the return of await is:  hello world (third line of async_function)
                       #        Im the yield function (first line of yield_function 
                       #              from the call in fourth line of async_function)
                       #        5 ( print(coro.send(None)) by itself )

print('send')          # prints send

print(coro.send(None)) # prints after yield (third line of yield_function)
                       # raise StopIteration: end of async
```

As you can see, we can go throw an async function as we did with a yield function. But async function hasnt `next()` (I dont know why) and `send()` can has just 'None' as parameter. For each `coro.send(None)` the function progress to the next `yield`, and exits to `await`, then the yielded value is again "yielded" by `await` and passed to the outer layer of the code `print(coro.send(None)`. At the next `send(None)` the progress continue right at the preceding `yield` to the next one. `print('send')` is used to have a hint about the point where the function stops. Furthermore, at the very end of the async function, a StopIteration is raised with the value returned if has one, like `yield` and `yield from`.

Its so important get the hint about how `async/await` really runs. Because I found really obscure the gap between generators and async/await, avoiding me to understand how asyncronous code is managed by python or asyncio itself. At the end, the matter of fact is, `async / await` is another layer of syntactic sugar on python, with an extra improve of readability and performance for the case was designed, stops and exits from functions progressions just to control the flow of those functions, and not to receive or send lazily some values, which is the purpose of generators.

## 1.5. Queues.

Queues (or Deques) are a "string" of objects interreferenced between them. Are based on a general idea named "linked list", which solve a performance issue of arrays (or list in python).

The performance issue of arrays is about array items have indexes, and when some item is deleted, items indexes after the deleted item must be updated. So, if you have an array with 5M items, and you delete the first item, 4.999.999 items must update their index. And that hurts a lot.

The solution of linked list is have a bunch of objects with a attribute holding the data and another attribute referencing the next object of the list. If is a single linked list, has just one attribute referencing the next object. If is a doubly linked list each object have another attribute referencing the preceding object aswell.

Linked list are useful to work with first and last items of a list. But not so efficient to iterate over the list because it must trace every object one by one and reference it to the list until it finds the desired object.

A queue is a list-like which we can receive and delete (`pop()`) the first item and add new items at the end of the list.
A deque, for instance, is a list-like which we can receive, delete and insert items at the end or start of a list.

Those capabilities of queues makes it ideal to algorithms with stacked data. Even if that stack are treated with FIFO (First In, First Out) or LIFO (Last In, First Out).

This will be really important for async managment. Spoiler alert: the event loop is a queue.

## 1.6. Selectors.

Python has a module named `selectors`. The defintion of [selectors module](https://docs.python.org/3/library/selectors.html) is: 

> "allows high-level and efficient I/O multiplexing"

But I think it is a bit obscure what this mean. My idea of multiplexation doesnt fit in what I understand about selectors module (but I must admit its behaves similarly).

Within a selector object you can register a bunch of IO objects (named by the module as `fileobj`) like a socket. At registration time, you must define to what event you want register your IO object (those events are `EVENT_READ` and `EVENT_WRITE`), and what is interested in the IO object when it will be ready to preform that event. When the IO object iis ready, the selector object add it to a list of ready IO objects list which you can get with `select()` method. Eg:

```python
from selectors import DefaultSelector, EVENT_READ

selector = DefaultSelector()
socket = # the code to make a socket connection

def read_socket(socket):
    # the code to read a message from socket
    
selector.register( socket, EVENT_READ, read_socket) # when socket is ready to read, will be added a to a list of ready sockets.

while True:
    events_ready = selector.select()    
    for ready_socket_info, event in events_ready:
        ready_socket_info.data(ready_socket_info.fileobj)
        # selector_return.data is what is interested in IO object when its ready. 
        # In this case, the function reference read_socket.
        # seletor_return.fileobj is the IO object itself.
```

So, selectors module monitoring whatever IO object you registered, and returns it when the IO Object is ready for the event which you resgister it with whatever you pass as data, being the data something interested in the IO Object.

The matter of fact of this also is, `selector.select()` expect as param a timeout. If timeout is `None` (de default value), `select()` will block the loop until some IO object is ready.

## 1.7. Finally, how asynchronous code works.

A simple asynchronous machinery can be separated in three blocks: an executor block, a monitoring block and a request block.

In the request block we have async functions which serves as interface for non async functions. Those async functions returns the IO object with we want preform something, the non async function we want preform and the event_name attached to the non async function, eg: an async function serving as interface for the non async function `socket.send()` will return the `EVENT_WRITE` name. In others words, returns the needed info to register an IO Object into a selector. They return the info to make a request to preform a non async function when the IO object is ready to preform it.

In the monitoring block is just the while loop above with the selector object returning those IO objects ready to preform something.

The executor object is an addition to the monitoring while loop, where the requested function is preformed and then `send(None)` to the async function to progress to the next `await` line where is requested another non async function to preform when the IO object is ready.

If you try to code your simple asynchronous code, you could see that no async functions is needed really. But probably that simple scenario is builded with functions with just one `await` line. The importance about `async/await` is the fact that we can gather various `await` calls in one function.

I wont write any sample code here because can be aa bit difficult to be properly documented. But I invite you to see [this fantastic PyCon conference by David Beazly](https://www.youtube.com/watch?v=ZzfHjytDceU) where he code an asynchronous engine.

# 2. AsyncIO.

## 2.1. Multithreading vs GIL.

Multithreads are the capability of a code to run things paralel. But in python that doesnt happen. Due to control the code flow and variables access, python has a machinery named GIL (Global Interpreter Locker). Per each interpreter, there is a GIL indicating what action must to be preformed. If you want to preform something paralel, you must to run another python interpreter with its own GIL.

Python, anyway, has a multithreading module, which makes a simulation of multithreads, switching the GIL between threads so quickly to aparently run a few things concurrently, but it is not the case really.

That produces a funny thing (not funny, indeed). Multithreads have some flaws named "race conditions". When a variable is read from a few threads at once, the madness can arrive. Race conditions can be the most difficult problem to solve in programming. And you must to deal with that in exchange to the capability to run more than one thing at once. But as I said, in python that doesnt happend, is simulated. So python multithreads gives you the flaws of multithreads, without the benefits.

In a concrete case, multithread can appear to work. When there os some blocking functions, leaving the thread on idle state. Just in that scenario, threads in python have a "benefit" because switching the GIL to an idle thread iis relatively cheap. But with just a few of threads. When you have a lot of threads, the machinery to identify all the threads and the time spend to switch the GIL hurts a lot.

This python flaw can be solved with asynchronous programming. You can use a lot of non blocking sockets that just consumes resources when they are ready to preform something, without the need of has overhead with multithreads or switch the GIL.

## 2.2. AsyncIO module.

In python we have a module named `AsyncIO` which provide us with an event loop (monitoring and executor block) and write high-level asyncrhonous code.

`AsyncIO` has a few names you must known: coroutines, tasks and futures.
* corountines are the returned object of an async function, as we saw before. In others words, an async function is a coroutine factory as a yield function is a generator factory.
* tasks are the code between two `await`s in a coroutine.
* futures are placeholder values. Tasks returns instantly a future as value. When the task finish, the future returned is set to a value.

I couldnt avoid to mention this module considering the topic of these notes, but the usage of `AsyncIO` is not my focus. There are a lot of articles and obviously the [`AsyncIO` documentation](https://docs.python.org/3/library/asyncio.html). I want to be focus on how asynchronous code works, whats solves against python multithreads flaws and how we could think about asynchronous code to get more benefits than we get with the common way to think about this topic. Although I will give for known certain basic things of `AsyncIO` in some points that I will write later.

# 3. Async multithreading?

## 3.1. An Asynchronous purpose twist.

Its not a big twist, really. Indeed is not a twist. Depends on whats your way to explain asynchronous programming and get a general idea that gather all the ways to explain it, and try to think how far we can go.

The most common I saw is: asynchronous programming is a way to do concurrent tasks in one thread. This explanation I think is common just in Python communities because the flaws on python threads was normalized, and with this, asyncrhonous code preform paralel tasks... but its not true, even if it appears it. Asynchronous means to do things without a concrete order, not concurrently or paralely.

A way more accurate explanation is: asynchronous programming avoid idle states in threads, preforming others tasks, postponing a preceding task while is waiting to be complete.

Idle states on threads becomes when we call a blocking function which waits for something be comepleted. And to understand this better, we must to know a bit about OSI model.

OSI model is a hierarchy structure of blocks. Each block is attached to a part of the PC machinery to work. The tops OSI blocks are attached to apps, mid blocks are about protocols like TCP/IP or HTTP more attached to OS and low blocks are physical parts like routers.

For example, when Python (attached to apps) wants to write a file in memory, calls to OS functions to save the data. That calls waits to OS response to know that the save was completed. So Python threads becomes idle until that response arrive. With sockets is so clear to see that situation, because must to wait the response from a server, being the most large wait.

Even save files or network request are IO bound tasks. And its the most common situation to has an idle thread. CPU bound tasks have no idle states because... they are doing things. But if we do multithreads to preform those CPU bound tasks, the main threads becomes idle waiting those subthreads join with results. And as I said before, multithreads can be dangerous if we have race conditions, but there are a lot of situations where multithreads are safe and hasnt race conditions at all.

But, in python we have the `AsyncIO` module. And as its name tell us, are just to IO bound tasks, and its pretty difficult figure out how to build a custom awaiteable function with subthreads. (furthermore the fact that multithreads in python are simulated). The objective is try to find the way to manage the `AsyncIO` event loop, to give the petition to await our own functions, but its pretty obscure in `AsyncIO` documentation how to do that. An approach is using future objects in some way and set the value of that future when the sub thread is completed. That could be done with Cython, but this is something that will be written later.

All of this drive us to something that is becoming more common in PCs.

## 3.2. Tasks Schedulers, IPC problems and Compute Express Link.

OS have their own tasks schedulers which assings the tasks to certain cores. Windows's task scheduler must to has some improvements and Microsoft is working on that, because this scheduler assignments are attached at tasks levels and not to process levels. This means that for certain process, a function is preformed in a core, but the next function could be preformed in another core. For Intels CPUs the connections between cores are so efficient, but for AMD Infinity Fabric connections it hurts a lot (and the succesfull of Ryzen 3 motivates Microsoft to improve their task scheduler). In Linux this not happen. Linux task scheduler is attached to process, so AMD CPUs dont waste time in just moving data between L1 caches.

Apart from this, CPUs by themselves wait to resources. In [Fluent Python book, page 552](https://www.amazon.com/Fluent-Python-Luciano-Ramalho/dp/1491946008/ref=sr_1_1?adgrpid=59964067361&gclid=Cj0KCQjwjrvpBRC0ARIsAFrFuV-9hXnKwDowMqcoscDXet3D0Mbm5FJs1K8Nh6RHZ-bEGvp3B_bXHyYaAl8bEALw_wcB&hvadid=275377512148&hvdev=c&hvlocphy=1005415&hvnetw=g&hvpos=1t1&hvqmt=e&hvrand=6055890989794178715&hvtargid=kwd-300008025082&hydadcr=6384_1820885&keywords=fluent+python&qid=1563429621&s=gateway&sr=8-1) you can see, for example, how a request to data saved in ram could spend 250 cpu cycles, if that data is in a HDD that waiting increases to 41000000 cpu cycles.

Nowadays we have CPUs with lithographs of 7 nm, and the usability of silicon ends at 1 nm. So its becoming more difficult achieve preformance improvents with mere hardware replacements. Its time to do logical and architecture improvements, like AMD chiplets.

On the other hand, Intel and a few manufacturers are investigating in something they call [Compute Express Link](https://www.computeexpresslink.org). One of the improvements is, precisely, asynchronous management. When you cant improve hardware power, the only way to improve performance is being more efficient on work avoiding waits, executing other things while the resources arrive. Therefore, asynchronous management is being implemented in low and medium OSI layers, and it is important to consider the implementation of asynchronous code in our apps to be more efficient.

# 4. AsyncIO difficulties and Cython possibilities.

This will be a short chapter because Im currently researching how to use properly Cython.

As I said before, `AsyncIO` is a bit obscure about how deal with its event loop at low level. Even `AsyncIO` devs talk about be more hermetic in low level layers of the module. So make our own event loop considering all the explanations at chapter 1 could be a possibility, but makes more difficult the usability of modules like `aiohttp` because those modules are focus on `AsyncIO`.

Anyway, with Cython we have the `nogil` functions attribute, that preform tasks outside the python interpreter and can preform things with real multithreads. And can be a posibility try to instace a future object at the start of our functions, return it to the event loop, which will be in the waiting state of the loop until the future has set its value, and after complete the subthread on Cython, set that future value.

When I progress in Cython's research and have proof of how it works I will be updating these notes.






