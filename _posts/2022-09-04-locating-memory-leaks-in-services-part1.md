---
layout: post
title:  "Locating memory leaks in a Python service – Part 1: Pure Python"
description: About pure Python memory issues in a FastAPI process
---
Even in a garbage-collected language like Python it is possible to create applications with memory leaks. This means that the program keeps memory reserved vor variables which are no longer needed. So the memory could be freed, but it isn't. Especially in long-running applications this can lead to a huge memory consumption over time, up to a point where the hardware limit is reached.
In a series of two blog posts I'll show how to debug such memory issues in a Python web service.

## Memory issues in long-running services
More than once I've seen that a shiny new version of a webservice turned out to be a black whole for computer memory. In the chart below you can see an actual example from a project I worked on. It is a webservice written in Python and deployed to a Kubernetes cluster. There is one Kubernetes deployment per country and the memory usage for all is large but quite stable if you don't consider the steps caused by autoscaling. Only for one of the services ("US"), a new version was deployed on 23 August and as soon as that had started up and got load you can see the steady increase in memory.

<img src="/assets/images/2022-06-18-locating-memory-leaks-in-python-webservices/memory-leak-in-prod.png" alt="Memory metrics of a web service with memory leak" style="width:80%;"/>

A simple, but relatively dump countermeasure is to implement some kind of an automated restart of the service as shown in the next example (green: the total number of requests, yellow dotted: reserved memory)
<img src="/assets/images/2022-06-18-locating-memory-leaks-in-python-webservices/sawtooth-pattern.png" alt="Memory metrics of a web service with sawtooth pattern" style="width:80%;"/>

This is from a service which restarts its workers every 2000 requests in order to mitigate a memory leak. This has some disadvantages. For example a few requests might run into server errors when workers are restarted. And of course constant restarts of services also put the infrastructure under unnecessary stress, because every restart might mean new scheduling and additional CPU, network and disk load. Therefore it is better to fix the root cause and I'll describe in the next sections how to identify where the memory leak comes from.


## Some basics of CPython's memory management
To have a little background when talking about the main types of memory issues in Python, let's have a very brief look into how memory is managed in Python's reference implementation "CPython". The basic scenario with only pure Python code looks like the following diagram:

<img src="/assets/images/2022-06-18-locating-memory-leaks-in-python-webservices/python-memory-model.svg" alt="The CPython memory model" style="width:80%;"/>

The variables in the stack frames of the CPython stack only contain references to objects which are all stored on the heap. Even simple types such as integers are stored there. But there can be multiple references to the same object on the heap. Every object has a reference counter and the Python runtime makes sure to delete objects which have no more references. But it is also possible to create circular references. Without special treatment they could not be deallocated anymore. This is done in CPython by a garbage collector. It runs every now and then and checks the heap for objects which can be deleted because they are no longer reachable from any reference variable on the stack.

Now let's go a step further and introduce some native extension code on top of the pure Python. Many popular Python packages contain such extensions which use natively compiled code (e.g. in C, C++ or Rust) which can be imported as Python module by the CPython interpreter. What this means for the memory management of a program is shown in the diagram below. The moment a C function is called, we are on a different kind of stack. Other than the Python stack it can also directly contain values and pointers to raw memory. Through the CPython API it can also create and hold references to objects on the Python heap. The important difference is that none of them are fully managed by the Python runtime. It is up to the C programmer to free memory and deallocate references to Python objects.

<img src="/assets/images/2022-06-18-locating-memory-leaks-in-python-webservices/python-memory-model-including-c.svg" alt="The CPython memory model including native function calls" style="width:80%;"/>

This is still quite simplified. There are many more complexities hidden in the CPython implementation. For example, just to name a few:
- The Python objects on the heap consist of a PyObject including a reference counter and a pointer to the separately stored value.
- Values of some types (e.g. integers, strings) get a special treatment and may not necessarily be deleted if the reference counter decreases to 0.
- Not only Python functions can call into C functions, but also the other direction is possible.
- One can create native Python objects also from C extensions.

However, in order to diagnose memory issues it is often sufficient to only understand which parts of the program are responsible for allocating the largest chunks of memory. Then one can dig deeper to understand the causes or just adjust the responsible lines of code until the situation improves.
In case of further interest I can recommend the following two articles as a starting point to learn more about memory management in Python:
- [Python Memory Management (Milind Deore)](https://medium.com/swlh/python-memory-management-7181d8a6ae5e)
- [Memory Management in Python (Alexander VanTol)](https://realpython.com/python-memory-management/)

Also the Python documentation itself contains a [detailed chapter about memory handling](https://docs.python.org/3/c-api/memory.html).

## Finding a memory leak in pure Python code

### Example service
For the purpose of simple demonstration we use a very simple webservice based on the FastAPI framework.
It has just a single GET endpoint "/leaky" which generates and returns a uuid. The code is very simple and maybe one can directly see that every result is also stored in the list `results` and never deleted:

```python

import uuid
import uvicorn
from fastapi import FastAPI, Response


app = FastAPI()
results = []

@app.get("/leaky")
async def leaky_endpoint():
    i = uuid.uuid4()
    results.append(i)
    return {"random UUID": i}


if __name__ == "__main__":
    uvicorn.run(app, port=8080, workers=1)

```

If we simulate some load and send a couple of thousand of requests to the service we can see that the memory grows proportionally to the number of requests:
<img src="/assets/images/2022-06-18-locating-memory-leaks-in-python-webservices/memory-growth-under-load.png" alt="Memory growth of the webservice under load" style="width:80%;"/>

### Overall process statistics

In order to diagnose where the memory leak comes from we will enrich the service by a couple of introspection endpoints. For the start let's just add some overall process information, similar to what the unix tool `ps` would show. This can be helpful if one wants to double-check that a memory issue indicated by the monitoring really comes to the service. Also it is possible that in a simpler setup such a monitoring doesn't even exist and there is also no direct option to execute a tool like `ps` on the host.

```python
import os
import psutil


@app.get("/pstats")
def pstats():
    process = psutil.Process(os.getpid())
    return {
        "rss": f"{process.memory_info().rss / 1024 ** 2:.2f} MiB",
        "vms": f"{process.memory_info().vms / 1024 ** 2:.2f} MiB",
        "shared": f"{process.memory_info().shared / 1024 ** 2:.2f} MiB",
        "open file descriptors": process.num_fds(),
        "threads": process.num_threads(),
    }
```
This returns a basic set of process statistics as json object. In can be extended easily on demand by further interesting metrics. Let's see what it gives us.

Memory usage just after startup:
```shell
❯ curl 'localhost:8080/pstats'
{"rss":"43.75 MiB","vms":"234.40 MiB","shared":"16.62 MiB","open file descriptors":15,"threads":6}
```

And after a couple of thousand requests:
```shell
❯ curl 'localhost:8080/pstats'
{"rss":"127.42 MiB","vms":"319.78 MiB","shared":"16.62 MiB","open file descriptors":15,"threads":6}%
```

The number for "rss" ([resident memory](https://en.wikipedia.org/wiki/Resident_set_size)) has already tripled, and it can also clearly be seen that the number of threads or open file descriptors is untouched. So we really have an issue with memory only.

### Python heap analysis with guppy3
The old, but still very valuable package [guppy3](https://pypi.org/project/guppy3/) can be used to analyze what kind of objects are on the Python managed part of the program's heap memory.

After installing the package "guppy3", the endpoint to do the analysis looks as simple as:
```python
import guppy
from fastapi.responses import PlainTextResponse


@app.get("/heap", response_class=PlainTextResponse)
def heap():
    h = guppy.hpy()
    return str(h.heap())
```

Its output gives us a table of the cumulative size of the objects on the heap, grouped by type. If we are lucky, a suspicious object type sticks out. In our example this is the case indeed. The table shows a large number of UUID and int objects, taking the majority of the allocated heap space:
```shell
❯ curl 'localhost:8080/heap'  
Partition of a set of 4698834 objects. Total size = 267772726 bytes.
 Index  Count   %     Size   % Cumulative  % Kind (class / dict of class)
     0 2257785  48 126435960  47 126435960  47 uuid.UUID
     1 2265983  48 99555488  37 225991448  84 int
     2   1490   0 19445560   7 245437008  92 list
     3  52759   1  5056975   2 250493983  94 str
     4  41399   1  2994576   1 253488559  95 tuple
     5  12147   0  2194602   1 255683161  95 types.CodeType
     6   2160   0  2128208   1 257811369  96 type
     7  20047   0  1626412   1 259437781  97 bytes
     8  11075   0  1594800   1 261032581  97 function
     9   3369   0  1211632   0 262244213  98 dict (no owner)
<595 more rows. Type e.g. '_.more' to view.>
```

This is enough already to search the code for references to UUID objects and to try and optimize the respective code sections.


### Looking for big memory blocks with tracemalloc
Guppy gives a cross-section of the memory allocation, a momentary view. Sometimes it is more useful to analyze the development over time. Especially when the service allocates a lot of memory already without a memory leak, it is otherwise hard to spot the issue. What may help here is the standard library module [tracemalloc](https://docs.python.org/3/library/tracemalloc.html). With tracemalloc it is possible to set a reference point and compare the composition of the Python heap at a later point in time to the reference point. If there are significant increases, they might be related to a memory leak.

For tracemalloc we add another diagnostics endpoint. It needs a few more lines of code to generate output which can be well digested.
```python
import re
from fastapi.responses import PlainTextResponse
import tracemalloc

first_trace = None


@app.get("/tracemalloc", response_class=PlainTextResponse)
def trace(n: int = 10, filter: str = ".*", v: bool = False):
    global first_trace

    # On first call: create reference point
    if not first_trace:  
        tracemalloc.start()
        first_trace = tracemalloc.take_snapshot()
        return "First snapshot taken!\n"

    # Subsequent calls: show changes
    else:  
        top_stats = tracemalloc.take_snapshot().compare_to(first_trace, "lineno")
        top_stats = [t for t in top_stats if re.search(filter, str(t))]
        if not v:
            return "\n".join([str(stat) for stat in top_stats[:n]])
        lines = []
        for stat in top_stats[:n]:
            lines.append(str(stat))
            lines.append(f"{stat.count} memory blocks: {stat.size/1024:.1f} KiB")
            for line in stat.traceback.format():
                lines.append(line)
            lines.append("")
        return "\n".join(lines)
```

This endpoint creates a reference snapshot when it is called for the first time.
From the second call on it prints statistics about the memory changes. They can be limited to the top `n` results and be filtered with a regular expression `filter`. Also there is a switch `v` for "verbose" in order to show a detailed stacktrace instead of a compact result.

Let's show it on an example. The first call is to set a reference point with tracemalloc:
```shell
❯ curl localhost:8080/tracemalloc
First snapshot taken!
```

A second call with the standard parameters shows the ten biggest blocks:
```shell
❯ curl localhost:8080/tracemalloc
~/code/blog/code/2022-06-18-locating-memory-leaks-in-python-webservices/api/api.py:24: size=16.3 MiB (+16.3 MiB), count=1 (+1), average=16.3 MiB
~/.pyenv/versions/3.10.3/lib/python3.10/uuid.py:715: size=13.3 MiB (+13.3 MiB), count=248153 (+248153), average=56 B
~/.pyenv/versions/3.10.3/lib/python3.10/uuid.py:220: size=10.4 MiB (+10.4 MiB), count=248153 (+248153), average=44 B
~/code/blog/code/2022-06-18-locating-memory-leaks-in-python-webservices/.venv/lib/python3.10/site-packages/fastapi/routing.py:251: size=13.5 KiB (+13.5 KiB), count=82 (+82), average=168 B
~/code/blog/code/2022-06-18-locating-memory-leaks-in-python-webservices/.venv/lib/python3.10/site-packages/fastapi/dependencies/utils.py:552: size=3864 B (+3864 B), count=69 (+69), average=56 B
~/.pyenv/versions/3.10.3/lib/python3.10/asyncio/runners.py:44: size=1792 B (+1792 B), count=10 (+10), average=179 B
~/.pyenv/versions/3.10.3/lib/python3.10/asyncio/locks.py:168: size=1656 B (+1656 B), count=11 (+11), average=151 B
~/code/blog/code/2022-06-18-locating-memory-leaks-in-python-webservices/.venv/lib/python3.10/site-packages/uvicorn/protocols/http/httptools_impl.py:253: size=1581 B (+1581 B), count=5 (+5), average=316 B
~/code/blog/code/2022-06-18-locating-memory-leaks-in-python-webservices/.venv/lib/python3.10/site-packages/starlette/routing.py:65: size=1552 B (+1552 B), count=3 (+3), average=517 B
~/.pyenv/versions/3.10.3/lib/python3.10/json/encoder.py:215: size=1472 B (+1472 B), count=23 (+23), average=64 B% 
```

The largest entry here is some entry in `api.py`. By using the filter, limit and verbosity arguments one can take a detailed look at the suspect:
```shell
❯ curl 'localhost:8080/tracemalloc?filter=api.py&n=1&v=true'
~/code/blog/code/2022-06-18-locating-memory-leaks-in-python-webservices/api/api.py:24: size=16.3 MiB (+16.3 MiB), count=1 (+1), average=16.3 MiB
1 memory blocks: 16726.8 KiB
  File "~/code/blog/code/2022-06-18-locating-memory-leaks-in-python-webservices/api/api.py", line 24
    results.append(i)
```
This clearly shows that we find the place where all these 16.3 MiB of memory were allocated in line 24 of our "api.py". This is the line where we `append()` the result to a list before we return it. So exactly the place where the memory is leaked.

## Summary
This first part of the series about  memory leaks shows how the memory model of CPython is designed and what the role of the garbage collector is. On a simple example service it is demonstrated how to analyze a leaky program and locate the place where memory is allocated which is not freed later.

As usual, the full source code is [available on Github](https://github.com/chr1st1ank/blog/tree/main/code/2022-09-locating-memory-leaks-in-python-webservices).

The example applies only to pure Python code. In a second post I will also show how to deal with a memory issue which is produced in native code embedded into a Python application. Stay tuned!
