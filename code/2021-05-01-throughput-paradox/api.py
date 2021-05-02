# Run with:
# uvicorn fastapi_main:app --workers 1 --limit-concurrency 1 --port 8080

# Test with:
# go run github.com/codesenberg/bombardier -c 4 -d 10s -l 'localhost:8080/calculate?argument=abc'
import asyncio
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


@app.get("/calculate")
async def get_calculate(input: str):
    x = calculate(input, 0.5)
    return {"result": x}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=8088, workers=1)

