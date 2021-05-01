# Run with:
# uvicorn fastapi_main:app --workers 1 --limit-concurrency 1 --port 8080

# Test with:
# go run github.com/codesenberg/bombardier -c 4 -d 10s -l 'localhost:8080/calculate?argument=abc'
import asyncio
import concurrent
import hashlib
from timeit import default_timer as timer

from fastapi import FastAPI, Response

app = FastAPI()


def calculate(input: str, timeout=0.5):
    """Dummy machine learning operation with fixed processing time"""
    start = timer()
    output = input
    m = hashlib.sha256()
    while timer() < start + timeout:
        m.update(output.encode('utf-8'))
        output = m.hexdigest()
    return output


@app.on_event("startup")
async def on_startup():
    workers = 1
    queue_length = 2
    app.state.pool = concurrent.futures.ProcessPoolExecutor(max_workers=workers)
    app.state.semaphore = asyncio.Semaphore(queue_length)


@app.get("/calculate")
async def get_calculate(input: str, response: Response):
    if app.state.semaphore.locked():
        response.status_code = 503
        return {"error": "Too many requests"}
    async with app.state.semaphore:
        loop = asyncio.get_running_loop()
        x = await loop.run_in_executor(app.state.pool, calculate, input, 0.5)
        return {"result": x}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=8088, workers=1)

