"""Example for using malloc/free with Cython.

Taken from: https://cython.readthedocs.io/en/latest/src/tutorial/memory_allocation.html
"""
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
        # Here we should return the allocated memory to the system:
        # free(my_array)
        pass
