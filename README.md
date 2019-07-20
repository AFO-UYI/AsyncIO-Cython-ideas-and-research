# AsyncIO + Cython (context, ideas and research)

While working on a personal project, I stumbled upon different needs that AsyncIO didn’t seem able to resolve. After further research into how asynchronous code works in Python, here’s what I learned. 



1. [Understanding how asynchronous code works.](https://github.com/AFO-UYI/AsyncIO-Cython-ideas-and-research#1-understanding-how-asynchronous-code-works)
    *   [Pointers and First Class Functions.](https://github.com/AFO-UYI/AsyncIO-Cython-ideas-and-research#11-pointers-and-first-class-functions)
    *   [Function contexts and closures.](https://github.com/AFO-UYI/AsyncIO-Cython-ideas-and-research#12-function-contexts-and-closures)
    *   [Yield, StopIteration error and Yield From.](https://github.com/AFO-UYI/AsyncIO-Cython-ideas-and-research#13-yield-stopiteration-error-and-yield-from)
    *   [Async/Await.](https://github.com/AFO-UYI/AsyncIO-Cython-ideas-and-research#14-asyncawait)
    *   [Queues.](https://github.com/AFO-UYI/AsyncIO-Cython-ideas-and-research#15-queues)
    *   [Selector.](https://github.com/AFO-UYI/AsyncIO-Cython-ideas-and-research#16-selectors)
    *   [Finally, how asynchronous code works.](https://github.com/AFO-UYI/AsyncIO-Cython-ideas-and-research#17-finally-how-asynchronous-code-works)
2. [AsyncIO.](https://github.com/AFO-UYI/AsyncIO-Cython-ideas-and-research#2-asyncio)
    *   [Multithreading vs GIL.](https://github.com/AFO-UYI/AsyncIO-Cython-ideas-and-research#21-multithreading-vs-gil)
    *   [AsyncIO module.](https://github.com/AFO-UYI/AsyncIO-Cython-ideas-and-research#22-asyncio-module)
3. [Async multithreading?](https://github.com/AFO-UYI/AsyncIO-Cython-ideas-and-research#3-async-multithreading)
    *   [An Asynchronous purpose twist.](https://github.com/AFO-UYI/AsyncIO-Cython-ideas-and-research#31-an-asynchronous-purpose-twist)
    *   [Tasks Schedulers, IPC problems and Compute Express Link.](https://github.com/AFO-UYI/AsyncIO-Cython-ideas-and-research#32-tasks-schedulers-ipc-problems-and-compute-express-link)
4. [AsyncIO difficulties and Cython possibilities.](https://github.com/AFO-UYI/AsyncIO-Cython-ideas-and-research#4-asyncio-difficulties-and-cython-possibilities)



---



# 1. Understanding how asynchronous code works.

In order to understand how the asynchronous concept came to be, there are a few steps involved into looking at Python and programming history. 


## 1.1. Pointers and First Class Functions.

First and foremost, I need to explain something that often seems to cause misconceptions. Variables are not values: they are memory addresses.

If, in Python, you have a variable like  `a = 10`, `a` is not necessarily 10, it is the memory address where 10 is saved. In memory you can hold values or instructions, and you have names which hold those values’ and instructions’ memory addresses. So, in reality, you can think about functions as a data type which can be called to perform something instead of just being plain values.

For this reason, you have lambda functions (or anon functions) being stored on a "variable". Eg:


```python
a_sum = lambda x, y: x+y

print(a_sum(3, 4)) # prints 7
```


This really does the same as usual `def` definitions in Python, and can be considered a syntactic sugar. As a matter of fact, if you are in PyCharm and you copy/paste the code above, the IDE will warn you that according to pep 8 guidelines, you’re not supposed to assign a lambda function.

With this, I want to point out that variables really are pointers. Depending on if a variable points to a plain value or an instruction, `()` could be added or not to that pointer name in order to run those instructions. In Python, if you use a function name without `()`, it will return a string with functions attributes, one of those usually are the memory address in hexadecimal format. With value pointers you can’t get the memory address that way because you will get the printed value, but if you use `id(variable_name)` you will get the memory address of that pointer in decimal. And because pointers are pointers, you can also run `id(function_name)` and you could see it’s the same memory address as the string printed at calling `function_name`without `()`, just one is in decimal and the other is in hexadecimal.

These pointers are interfaces to play with instructions and values, makes those functions in python get some special capabilities. Those functions with special capabilities are named first class functions, which can be treated the same way we treat values.


## 1.2. Function contexts and closures.

In Python, one of the special capabilities of functions to be first class functions is that functions are instance of the Object type. That means, functions have some attributes stored on a dictionary where things such as local variables references or parameters are held. Those attributes are called the context of a function and is created at defition time (when interpreter hits a `def` line).

As stated above, first class functions can be treated as we treat variables, and one of these treats is that we can declare new functions inside a function.


```python
def generator_function():

    def generated_function():
        print('Im a generated function')

    return generated_function     # we return the address, not a call ( generated_function without () )

g = generator_function()
print(g)       # prints <function generator_function.<locals>.generated_function at 0x000001BD58FE5048>
g()            # prints Im a generated function
```


When we call `g = generator_function()` interpreter hits `def generated_function`, instance an Object for `generated_function`and stores it in memory and gives it to `g` the memory address.

An interesting thing here is... If `generator_function` has some local variables, for `generated_functions` those variables will be like globals. Context for `generated_functions` is created at `generator_function` call, so in `generated_function` context will be that variables in context. Those variables are called closures.


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


In the code above, `generator_function` has a local variable named `closure_variable` and is used by `generated_function`. When interpreter hits `def generaated_function` creates an Object with attributes like `__code__.co_freevars` and `__closure__[0].cell_contents` where are stored the name and value of the closure respectively.

You can even change the value of those closures using the `nonlocal` keyword.


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


For each counter you create with `generator_function` the counter will start at 0, because the local variable of `generator_function` is 0 and when you call it, a new Object with its own context is created. Furthermore, a handy use case for this is that you can do other things between calls.


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

The `yield` keyword is comparable to syntactic sugar in the sense that it creates generators like in the code above, but it adds some extra things improving usability and capabilities. To define a generator with yield:


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


Now, we don’t need nested functions defined inside, or nonlocal variables. We just need to add `yield` at some point, and call the generator object throw `next()` instead of calling the generator by adding `()`.

What really is happening with `yield` is more interesting. `yield` stops and exits the execution of a function when interpreter hits the `yield` line, but the progress of that function is saved as a context update. So, in the first `next(counter)`, function hits `yield print(counter)`, stops and exits. Then, in the next `next(counter)` , count increments by 1 and again at `yield print(counter)` stops and exits, but now the context function was updated being count value equal to 1. And that happens every `next(counter)` call.

`yield` also has the capability to return values. So the code above could be:


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


Now the `count` value is returned and must be printed outside the function. This with the closure way must be different because the only way to return something is with the `return` keyword, and any extra operations must be called before `return`. `yield` is more comfortable and flexible to some situations.

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


In these cases, `yield` stops the functions right at the assignment step, that means, `count = yield` will be performed in the next call. So, each step starts on the assignment and stops at the return of count. That’s why counter is printing the value we are sending.

`next()` really is a `counter.send(None)` , both calls are the same. The first call of counter must be like that because it starts from the very first line of the function, and no assignment with `yield` is performed there. The `next()` call stops right at the first assignment with `yield`.

Just like with closures, other things can be performed between `next` or `send` calls.

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

We can also see that if we attempt to call counter 4 times when the function only has 3 yields, a StopIteration error is raised. StopIteration is normal and totally useful for those generators with uncertain finishes inside loops. We must remember to catch the exception and prevent our apps from stopping.

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


The returned value will be the StopIteration message. This message can be caught with:


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


In addition, we have the `yield from` keyword. A `yield from` in a function body produces a generator function as well. But this generator yields over another generator. `yield from` automatically handles everything over the generator which is yielding, even the StopIteration. In the case that a value is returned at StopIteration raising, the value will be returned in the `yield from` line. `yield form` has its own StopIteration to be controlled when the iteration is finished. Some examples:


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


We must catch that StopIteration of `another_yield_function` as we did before. If we want to do something with the returned value by `yield_function` we just must return it on `another_yield_function` as well.


```python
def another_yield_function():
    x = yield from yield_function() # (x = 'something after yields') when yield_function raise StopIteration
    return x

...

print(counter.send(42))   # prints 42
print(next(counter))      # raise StopIteration: something after yields.
```


The point is that, whatever we return in a generator, will be displayed as StopIteration value.

You can see that in a macro view of the code behaviour `yield from` has the same needs and performs just like plain `yield`. You can think of `yield from` as a tunnel between the outest and most internal generators. The real value of `yield from` is its capability to gather multiple generators.


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


In this example, you can also see that `yield from` can yield over iterables. Indeed, an iterable object must have an `__iter__` method defined that returns an iterator, which in essence is a generator.


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

`Async / Await` is a specialization of a `yield` use case. In the examples above, we use `yield `and `yield from` for simple iterations. It’s useful if you don’t want the entire list at once. But as previously stated, functions in Python are first class functions and can be used as a variable, so you can yield over an iterable of functions.


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


`async / await` exists for readability and optimizations, and it also creates a new way to think in code design. But it works pretty much the same way under the hood, closer to  `yield from` than `yield`. Eg:


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


As you can see, we can throw an async function just like we did with a yield function. But the async function has no `next()` (I don’t know why) and `send()` can have just 'None' as parameter. For each `coro.send(None)` ,the function progresses to the next `yield`, and exits to `await`, then the yielded value is again "yielded" by `await` and passed to the outer layer of the code `print(coro.send(None)`. At the next `send(None),` the progress continue right at the preceding `yield` to the next one. `print('send')` is used to get a hint about the point where the function stops. Furthermore, at the very end of the async function, a StopIteration is raised with the value returned if it has one, like `yield` and `yield from`.

It’s very important to understand how `async/await` really runs. Initially, I found a really obscure gap between generators and async/await, keeping me from understanding how asynchronous code is managed by Python or AsyncIO itself. At the end of the day, the matter of fact is that `async / await` is another layer of syntactic sugar on Python, with an extra improvement on readability and performance for the case it was designed for, stops and exits from functions progressions just to control the flow of those functions, and not to receive or lazily send some values, which is the purpose of generators.


## 1.5. Queues.

Queues (or Deques) are a "string" of objects interreferenced between them. They are based on a general idea named "linked list", which solves a performance issue of arrays (or list in Python).

The performance issue with arrays is that array items have indexes, and when an item is deleted, item indexes after the deleted item must be updated. So, if you have an array with 5MM items and you delete the first item, 4.999.999 items must update their index. That hurts. A lot. 

The solution is to have a bunch of objects with an attribute holding the data, and another attribute referencing the next object of the list. If it’s a single linked list, it has just one attribute referencing the next object. If it’s a doubly linked list, each object has another attribute referencing the preceding object as well.

Linked list are useful for working with first and last items of a list. But they’re not so efficient for iterating over the list because it must trace every object one by one and reference it to the list until it finds the desired object.

A queue is a list-like which we can receive and delete (`pop()`) the first item and add new items at the end of the list. A deque, for instance, is a list-like which we can receive, delete and insert items at the end or start of a list.

Those capabilities of queues makes them ideal for algorithms with stacked data. Even if those stack are treated with FIFO (First In, First Out) or LIFO (Last In, First Out).

This will be really important for async management. Spoiler alert: the event loop is a queue.


## 1.6. Selectors.

Python has a module named `selectors`. The definition of [selectors module](https://docs.python.org/3/library/selectors.html) is:

"allows high-level and efficient I/O multiplexing"

But I think what this really means is a bit obscure. My idea of multiplexation doesn’t fit in what I understand about selectors module (but I must admit its behaves similarly).

Within a selector object, you can register a bunch of IO objects (named by the module as `fileobj`) like a socket. At registration time, you must define to which event you want to register your IO object to (those events are `EVENT_READ` and `EVENT_WRITE`), and what is interested in the IO object when it will be ready to perform that event. When the IO object is ready, the selector object adds it to a list of available IO objects list which you can get with `select()` method. Eg:


```python
from selectors import DefaultSelector, EVENT_READ

selector = DefaultSelector()
socket = # the code to make a socket connection

def read_socket(socket):
    # the code to read a message from socket


selector.register( socket, EVENT_READ, read_socket) # when socket is ready to read, will be added to a list of ready sockets.

while True:
    events_ready = selector.select()    
    for ready_socket_info, event in events_ready:
        ready_socket_info.data(ready_socket_info.fileobj)
        # selector_return.data is what is interested in IO object when its ready. 
        # In this case, the function reference read_socket.
        # seletor_return.fileobj is the IO object itself.
```


So, selectors module monitoring whatever IO object you registered, and returns it when the IO Object is ready for the event which you register it with whatever you pass as data, being the data something interested in the IO Object.

As a matter of fact, `selector.select()` expects as param a timeout too. If timeout is `None` (the default value), `select()` will block the loop until an IO object is ready.


## 1.7. Finally, how asynchronous code works.

A simple asynchronous machinery can be separated in three blocks: an executor block, a monitoring block and a request block.

In the request block we have async functions which serves as an interface for non async functions. Those async functions return the IO object we want to perform something with, the non async function we want to perform and the event_name attached to the non async function, eg: an async function serving as interface for the non async function `socket.send()` will return the `EVENT_WRITE` name. In other words, it returns the info needed to register an IO Object into a selector. They return the info to make a request to perform a non async function when the IO object is ready to perform it.

The monitoring block is just the while loop above with the selector object returning those IO objects ready to perform something.

The executor object is an addition to the monitoring while loop, where the requested function is performed and then `send(None)` to the async function to progress to the next `await` line where another non async function is requested to perform when the IO object is ready.

If you try to code a simple asynchronous code, you could see that no async function is needed really. But probably that simple scenario is built with functions with just one `await` line. The importance about `async/await` is the fact that we can gather various `await` calls in one function.

I won’t write any sample code here because it can be complicated to document it properly, but I encourage you to watch [this fantastic PyCon conference by David Beazly](https://www.youtube.com/watch?v=ZzfHjytDceU) where he codes an asynchronous engine.


# 2. AsyncIO.


## 2.1. Multithreading vs GIL.

Multithreads give code he capability to run things parallelly. But in Python, that doesn’t happen. Given that Python needs to control the code flow and variable access, it has a system named GIL (Global Interpreter Locker). Per each interpreter, there is a GIL indicating what action must be performed. If you want to perform something parallelly, you must run another Python interpreter with its own GIL.

Python, anyway, has a multithreading module, which makes a simulation of multithreads, switching the GIL between threads so quickly to seemingly run a few things concurrently, but it’s really not the case.

That produces a funny thing (not funny, indeed). Multithreads have some flaws named "race conditions". When a variable is read from multiple threads at once, madness ensues. Race conditions can be the most difficult problem to solve in programming. And you must deal with those in exchange to the capability to run more than one thing at once. But as mentioned above, in Python that doesn’t actually happen, it is simulated. So Python multithreads gives you the flaws of multithreads, without the benefits.

In a concrete case, multithreads can appear to work. When there are some blocking functions, leaving the thread on idle state. Just in that scenario, threads in Python have a "benefit" because switching the GIL to an idle thread is relatively resource efficient. But this works only with a limited amount of threads. When you have a lot of them, the system that identifies all the threads and thus the time spent to switch the GIL hurts a lot.

This Python flaw can be solved with asynchronous programming. You can use a lot of non-blocking sockets that only consume resources when they are ready to perform something, without the need of having overhead with multithreads or switching the GIL.


## 2.2. AsyncIO module.

In Python we have a module named `AsyncIO` which provides us with an event loop (monitoring and executor block) and writes high-level asynchronous code.

`AsyncIO` has a few names you must know: coroutines, tasks and futures.



*   Coroutines are the returned object of an async function, as we saw before. In other words, an async function is a coroutine factory as a yield function is a generator factory.
*   Tasks are the code between two `await`s in a coroutine.
*   Futures are placeholder values. Tasks return instantly a future as a value. When the task finishes, the future returned is set to a value.

I couldn’t help mentioning this module considering the scope of these notes, but the usage of `AsyncIO` is not my focus. There are a lot of articles and naturally there’s the  <code>[AsyncIO documentation](https://docs.python.org/3/library/asyncio.html)</code>. I want to focus on how asynchronous code works, what it solves against Python multithread flaws and how we could think about asynchronous code to get more benefits than we get with the traditional way of going around this topic. That said, I will assume there is an understanding of <code>AsyncIO </code>basic concepts that I’ll refer to later.


# 3. Async multithreading?


## 3.1. An Asynchronous purpose twist.

It’s not a big twist, really. Indeed, it’s not a twist. It depends on your way of explaining asynchronous programming and having a general idea that gathers all the ways to explain it, and trying to think how far we can go.

The most common I saw is: asynchronous programming is a way to do concurrent tasks in one thread. I think this explanation is common mostly in Python communities because the flaws on Python threads were normalized, and with this, asynchronous code performs parallel tasks... but it’s not really true, even if it seems like it. Asynchronous means to do things without a concrete order, not necessarily concurrently or parallelly.

A way more accurate explanation is: asynchronous programming avoids idle states in threads, performing other tasks, postponing a preceding task while it’s waiting to be completed.

Idle states on threads happen when we call a blocking function which waits for something to be completed. And to understand this better, we must know a bit about OSI model.

OSI model is a hierarchy structure of blocks. Each block is attached to a part of the PC machinery to work. The top OSI blocks are attached to apps, mid blocks are about protocols like TCP/IP or HTTP more attached to OS and low blocks are physical parts like routers.

For example, when Python (attached to apps) wants to write a file in memory, it calls to OS functions to save the data. That call waits for the OS response to know that the save was completed. So Python threads become idle until that response arrives. With sockets it’s easier to see that situation, because they must wait for a response from the server, that being the longest wait.

Even save files or network requests are IO bound tasks. And that’s the most common situation to have an idle thread. CPU bound tasks have no idle states because... they are doing things. But if we do multithreads to perform those CPU bound tasks, the main threads become idle waiting for those subthreads to join with results. And as mentioned above, multithreads can be dangerous if we have race conditions, but there are a lot of situations where multithreads are safe and don’t have race conditions at all.

But, in Python we have the `AsyncIO` module. And as its name tells us, they are for IO bound tasks only, and it’s pretty difficult to figure out how to build a custom awaitable function with subthreads. (Even more so, given the fact that multithreads in Python are simulated). The objective is to try to find a way to manage the `AsyncIO` event loop, to give the petition to await for our own functions, but it’s pretty obscure in `AsyncIO` documentation to find how to do that. A potential approach is using future objects in some way and set the value of that future when the sub thread is completed. That could be done with Cython, but this is something that will be written later.

All of this drives us to something that is becoming more common in PCs.


## 3.2. Tasks Schedulers, IPC problems and Compute Express Link.

OS have their own task schedulers which assigns the tasks to certain cores. Windows's task scheduler needs some improvements and Microsoft is working on that, because this scheduler’s assignments are attached to tasks levels and not process levels. This means that for certain process, a function is performed in a core, but the next function could be performed in another core. For Intel’s CPUs the connections between cores are so efficient, but for AMD Infinity Fabric connections it hurts a lot (and the success of Ryzen 3 motivates Microsoft to improve their task scheduler). In Linux this does not happen. Linux’s task scheduler is attached to processes, so AMD CPUs don’t waste time in just moving data between L1 caches.

Aside from this, CPUs wait for resources themselves. In the [Fluent Python book, page 552](https://www.amazon.com/Fluent-Python-Luciano-Ramalho/dp/1491946008/ref=sr_1_1?adgrpid=59964067361&gclid=Cj0KCQjwjrvpBRC0ARIsAFrFuV-9hXnKwDowMqcoscDXet3D0Mbm5FJs1K8Nh6RHZ-bEGvp3B_bXHyYaAl8bEALw_wcB&hvadid=275377512148&hvdev=c&hvlocphy=1005415&hvnetw=g&hvpos=1t1&hvqmt=e&hvrand=6055890989794178715&hvtargid=kwd-300008025082&hydadcr=6384_1820885&keywords=fluent+python&qid=1563429621&s=gateway&sr=8-1) you can see, for example, how a request for data saved in RAM could spend 250 CPU cycles, and if that data is in a HDD the same wait increases to 41000000 CPU cycles.

Nowadays we have CPUs with lithographs of 7 nm, and the usability of silicon ends at 1 nm. So, it’s becoming increasingly difficult to achieve performance improvements with mere hardware upgrades. It’s time to do logical and architecture improvements, like AMD chiplets.

On the other hand, Intel and a few manufacturers are investigating something they call [Compute Express Link](https://www.computeexpresslink.org/). One of the improvements is, precisely, asynchronous management. When you can’t improve hardware power, the only way to improve performance is being more efficient with work by avoiding wait times, executing other things while the resources arrive. Therefore, asynchronous management is being implemented in low and medium OSI layers, and it is important to consider the implementation of asynchronous code in our apps to be more efficient.


# 4. AsyncIO difficulties and Cython possibilities.

I’m currently researching how to use Cython properly, so this may be a short chapter for the time being. 

As mentioned, `AsyncIO` is a bit obscure about how to deal with its event loop at the low level. So while making our own event loop considering all the explanations at chapter 1 could be a possibility, it may make it more difficult for the usability of modules like `aiohttp` because those modules are focused on `AsyncIO`.

Anyway, with Cython we have the `nogil` functions attribute, that performs tasks outside the Python interpreter and can perform things with real multithreads. And it can be a possibility to try to instance a future object at the start of our functions, return it to the event loop, which will be in the waiting state of the loop until the future has set its value, and after completing the subthread on Cython, set that future value.

When I further progress in Cython's research and have a better grasp of how it works, I’ll be updating these notes. 
