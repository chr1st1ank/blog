---
layout: post
title:  "Locating memory leaks in a Python service – Part 2: C-Extensions"
description: About memory issues of extension modules in a FastAPI process
---

**todo: intro**

## Locating a memory issue in a compiled extension module
Now we have the tools to clearly diagnose a memory leak in pure Python. So let's proceed to the next level and add some native code to the picture.
It is one of the strengths of Python how easy it can be extended with compiled code e.g. in C, by so called "extension modules". This is a key factor which made Python the first choice for data science: The heavy number crunching can be done by optimized routines and the program logic is written in the high-level Python language.

The drawback of course is, that any small flaw in the native code might lead to hard-to-debug memory issues in an application. Take a look into the section about reference counting in the [CPython extension guide](https://docs.python.org/3/extending/extending.html#reference-counts) to get an impression of how easy it is to forget a `Py_DECREF()` call to decrement the reference counter or to forget a `free()` call in case of memory allocated directly from C. Of course the risk can be reduced by sticking to certain standard patterns or by using a different language such as Rust or Cython for an extension. Nevertheless it is good to know how to identify memory issues in compiled extensions.

### Example
In order to show how to identify a memory leak in a compiled extension, we can use a simple Cython module. Cython allows to write a C extension in a syntax very close to Python. It gets transpiled to C and the compiled by Cython.

The Cython documentation provides us with a [good example](https://cython.readthedocs.io/en/latest/src/tutorial/memory_allocation.html) on how to use manual memory allocation with malloc/free. We can modify it a little bit to create a nice memory leak:

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

## Summary
