# Run with:
# python api/api.py

# Test with:
# go run github.com/codesenberg/bombardier -c 4 -d 10s -l 'localhost:8080/leaky'

# valgrind --leak-check=full ./.venv/bin/python api/api.py
# valgrind --leak-check=full --show-leak-kinds=all --trace-children=yes python api/api.py

import uuid
from fastapi import FastAPI, Response


app = FastAPI()


results = []


@app.get("/leaky")
async def leaky_endpoint():
    i = uuid.uuid4()
    results.append(i)
    return {"random UUID": i}


import native


@app.get("/leaky-native")
async def leaky_native_endpoint():
    i = native.random_noise()
    # results_native.append(i)
    return {"random UUID": i}


import re
from fastapi.responses import PlainTextResponse
import tracemalloc

first_trace = None


@app.get("/tracemalloc", response_class=PlainTextResponse)
def trace(n: int = 10, filter: str = ".*", v: bool = False):
    global first_trace

    if not first_trace:
        tracemalloc.start()
        first_trace = tracemalloc.take_snapshot()
        return "First snapshot taken!\n"
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


import gc


@app.get("/collect")
def collect(generation: int = 0):
    if generation:
        gc.collect(generation)
        return f"Ran gc.collect({generation})!"
    else:
        gc.collect()
        return f"Ran gc.collect()!"


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


import guppy
from fastapi.responses import PlainTextResponse


@app.get("/heap", response_class=PlainTextResponse)
def heap():
    h = guppy.hpy()
    return str(h.heap())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8080, workers=1)
