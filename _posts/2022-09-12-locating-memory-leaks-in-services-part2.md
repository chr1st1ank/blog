---
layout: post
title:  "Locating memory leaks in a Python service – Part 2: C-Extensions"
description: About memory issues of extension modules in a FastAPI process
---

**Building up on last week's issue about diagnosing memory leaks in Python, this blog post will show how to identify memory issues in native extension modules.**

From [the first posting]({% post_url 2022-09-04-locating-memory-leaks-in-services-part1 %}) 
we have the tools to clearly diagnose a memory leak in pure Python. So let's proceed to the next level and add some native code to the picture.
It is one of the strengths of Python how easy it can be extended with compiled code e.g. in C, by so called "extension modules". This is a key factor which made Python the first choice for data science: The heavy number crunching can be done by optimized routines and the program logic is written in the high-level Python language.

The drawback of course is, that any small flaw in the native code might lead to hard-to-debug memory issues in an application. Take a look into the section about reference counting in the [CPython extension guide](https://docs.python.org/3/extending/extending.html#reference-counts) to get an impression of how easy it is to forget a `Py_DECREF()` call to decrement the reference counter or to forget a `free()` call in case of memory allocated directly from C. Of course the risk can be reduced by sticking to certain standard patterns or by using a different language such as Rust or Cython for an extension. Nevertheless it is good to know how to identify memory issues in compiled extensions, because it can hit you earlier than you might expect. I first encountered such an issue when using a database driver which was partially written in Cython.

### Example in Cython
In order to show how to identify a memory leak in a compiled extension, we can use a simple [Cython](https://cython.org/) module. Cython allows to write a C extension in a syntax very close to Python. It gets transpiled to C and then compiled to machine code by Cython.

The Cython documentation provides us with a [good example](https://cython.readthedocs.io/en/latest/src/tutorial/memory_allocation.html) on how to use manual memory allocation with malloc/free. I modified it a little bit to create a nice memory leak. The `free()`call for an array is commented out:

```cython

import random
from libc.stdlib cimport malloc, free

def random_noise(int number=4):
    cdef int i
    # allocate number * sizeof(double) bytes of memory
    cdef double *my_array = <double *> malloc(number * sizeof(double))
    if not my_array:
        raise MemoryError()

    try:
        ran = random.normalvariate
        for i in range(number):
            my_array[i] = ran(0, 1)

        return [x for x in my_array[:number]]
    finally:
        ## Here we should return the allocated memory to the system:
        # free(my_array)
        ## But we don't:
        pass
```

Similar to the other examples from the first blog posts, the leaky function `random_noise` is used in an endpoint of a fastapi webservice as follows:

```python

import native

@app.get("/leaky-native")
async def leaky_native_endpoint():
    i = native.random_noise()
    return {"random UUID": i}

```
So, the Python codes looks perfectly fine and doesn't give any hint that the native code of the function `random_noise()` leaks memory.

### Observing the memory leak
Now let's start the webservice and send it a load of test requests. Watching the metrics we can clearly see how the memory footprint increases whenever there is CPU load, i.e. when requests are served:

<img src="/assets/images/2022-09-locating-memory-leaks-in-python-webservices/memory-growth-native-leak.png
" alt="Memory growth of the webservice under load" style="width:80%;"/>

In a first attempt we can now use the diagnostics endpoints introduced in the first posting about the topic. `/pstats` confirms the observed memory footprint of 92 MiB.
```console
$ curl 'localhost:8080/pstats'
{"rss":"92.04 MiB","vms":"277.95 MiB","shared":"16.34 MiB","open file descriptors":15,"threads":6}
```

The Python heap analysis with guppy on the `/heap` endpoint shows the space occupied by Python objects.
```console
$ curl 'localhost:8080/heap'  
Partition of a set of 182564 objects. Total size = 22632665 bytes.
 Index  Count   %     Size   % Cumulative  % Kind (class / dict of class)
     0  52096  29  4942951  22   4942951  22 str
     1  41394  23  2994232  13   7937183  35 tuple
     2  12147   7  2191183  10  10128366  45 types.CodeType
     3   2160   1  2127800   9  12256166  54 type
     4  20024  11  1625434   7  13881600  61 bytes
     5  11075   6  1594800   7  15476400  68 function
     6   3369   2  1211336   5  16687736  74 dict (no owner)
     7   2160   1   998040   4  17685776  78 dict of type
     8    599   0   892752   4  18578528  82 dict of module
     9      1   0   256536   1  18835064  83 uvloop.Loop
```

So the Python heap can only explain 22 of 92 MiB. 70 MiB are unexplained, because they are hidden in the heap space allocated by the C extension outside the control of the Python runtime.

### Analyzing the Python service with Valgrind
So, for the C extension a different tooling is necessary. Luckily also the C ecosystem provides tools which can be used for this purpose. What works well in this case is [Valgrind](https://valgrind.org/), a 20 years old, but still actively developed, instrumentation framework for C/C++ applications. It can be used to run another application and measure its memory allocations and deallocations. When the process stops, it prints detailed reports of memory sections which are possibly not deallocated properly.

We can run our test API with `valgrind --leak-check=full` to get some insights about unsafely handled memory:

```console
$ valgrind --leak-check=full ./.venv/bin/python api/api.py
==53120== Memcheck, a memory error detector
==53120== Copyright (C) 2002-2022, and GNU GPLd, by Julian Seward et al.
==53120== Using Valgrind-3.19.0 and LibVEX; rerun with -h for copyright info
==53120== Command: ./.venv/bin/python api/api.py
==53120== 
INFO:     Started server process [53120]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)
INFO:     127.0.0.1:41306 - "GET /leaky-native HTTP/1.1" 200 OK
...
INFO:     127.0.0.1:41320 - "GET /leaky-native HTTP/1.1" 200 OK
INFO:     127.0.0.1:41306 - "GET /leaky-native HTTP/1.1" 200 OK
^CINFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [53120]
==53120== 
==53120== HEAP SUMMARY:
==53120==     in use at exit: 2,053,110 bytes in 2,981 blocks
==53120==   total heap usage: 50,963 allocs, 47,982 frees, 52,546,348 bytes allocated
==53120== 
...
==53120== 
==53120== 34,816 bytes in 1,088 blocks are definitely lost in loss record 452 of 466
==53120==    at 0x4841888: malloc (in /usr/lib/valgrind/vgpreload_memcheck-amd64-linux.so)
==53120==    by 0x730D948: __pyx_pf_3api_6native_random_noise (native.c:1378)
==53120==    by 0x730D948: __pyx_pw_3api_6native_1random_noise (native.c:1335)
==53120==    by 0x333E8A: cfunction_call (methodobject.c:543)
==53120==    by 0x179D33: _PyObject_MakeTpCall (call.c:215)
==53120==    by 0x169439: _PyObject_VectorcallTstate (abstract.h:112)
==53120==    by 0x169439: _PyObject_VectorcallTstate (abstract.h:99)
==53120==    by 0x169439: PyObject_Vectorcall (abstract.h:123)
==53120==    by 0x169439: call_function (ceval.c:5867)
==53120==    by 0x169439: _PyEval_EvalFrameDefault (ceval.c:4181)
==53120==    by 0x327414: _PyEval_EvalFrame (pycore_ceval.h:46)
==53120==    by 0x327414: gen_send_ex2 (genobject.c:213)
==53120==    by 0x16A799: _PyEval_EvalFrameDefault (ceval.c:2586)
==53120==    by 0x327414: _PyEval_EvalFrame (pycore_ceval.h:46)
==53120==    by 0x327414: gen_send_ex2 (genobject.c:213)
==53120==    by 0x16A799: _PyEval_EvalFrameDefault (ceval.c:2586)
==53120==    by 0x327414: _PyEval_EvalFrame (pycore_ceval.h:46)
==53120==    by 0x327414: gen_send_ex2 (genobject.c:213)
==53120==    by 0x16A799: _PyEval_EvalFrameDefault (ceval.c:2586)
==53120==    by 0x327414: _PyEval_EvalFrame (pycore_ceval.h:46)
==53120==    by 0x327414: gen_send_ex2 (genobject.c:213)
==53120== 
==53120== LEAK SUMMARY:
==53120==    definitely lost: 34,816 bytes in 1,088 blocks
==53120==    indirectly lost: 0 bytes in 0 blocks
==53120==      possibly lost: 41,776 bytes in 70 blocks
==53120==    still reachable: 1,976,518 bytes in 1,823 blocks
==53120==         suppressed: 0 bytes in 0 blocks
==53120== Reachable blocks (those to which a pointer was found) are not shown.
==53120== To see them, rerun with: --leak-check=full --show-leak-kinds=all
==53120== 
==53120== For lists of detected and suppressed errors, rerun with: -s
==53120== ERROR SUMMARY: 44 errors from 44 contexts (suppressed: 0 from 0)
```

This report is shortened to the interesting core. There are also lots of "loss records" which are not related to the test setup but which refer also to far smaller memory sections. Each of these loss reports show the size of the memory block in bytes and the stacktrace of the functions allocating the memory. The example above shows the report for the biggest memory section which refers to 42 KiB of "possibly lost" memory. And indeed it mentions the file "native.c" which comes from the little Cython extension created as example.

If we follow the pointer to "native.c", line 1378, we find the following:
```c
  /* "api/native.pyx":11
 *     cdef int i
 *     # allocate number * sizeof(double) bytes of memory
 *     cdef double *my_array = <double *> malloc(number * sizeof(double))             # <<<<<<<<<<<<<<
 *     if not my_array:
 *         raise MemoryError()
 */
  __pyx_v_my_array = ((double *)malloc((__pyx_v_number * (sizeof(double)))));
```
The file "native.c" is autogenerated by Cython from "native.pyx". This doesn't make the code particularly readable. But luckily Cython also copies the lines from the `pyx` file as comment in, so that one can more easily refer to the code written by hand. And in the example we find exactly the line where the array is allocated whose `free()` is commented out to create the memory leak.
So the memory leak is correctly identified by Valgrind and could be fixed.

## Summary
This second episode about memory leaks shows how to identify missing memory de-allocations in native Python extensions. For such cases tools for Python memory analysis don't help anymore. But it is possible to use tools designed for the C language to successfully trace the sources of memory waste.

Both postings together provide a recipe which can be used in any long-running application to analyze if the memory management can be improved.

The source code of the examples is [available on Github](https://github.com/chr1st1ank/blog/tree/main/code/2022-09-locating-memory-leaks-in-python-webservices).

