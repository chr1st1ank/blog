"""Dummy Python API which behaves like a machine learning service.

Dependencies (install with pip):
 - fastapi
 - uvicorn

Run with:
    uvicorn api:app --workers 1 --port 8080
"""
import hashlib
from timeit import default_timer as timer
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    """The API's health endpoint"""
    return {"status": "ok"}

@app.get("/calculate")
async def get_calculate(input: str):
    """Some other endpoint doing a CPU intensive operation"""
    return {"input": input, "result": _calculate(input)}

def _calculate(input: str):
    """Do important calculations for 200ms"""
    start = timer()
    m = hashlib.sha256()
    m.update(input.encode('utf-8'))
    output = m.hexdigest()
    while start + 0.2 > timer():
        m.update(output.encode('utf-8'))
        output = m.hexdigest()
    return output
