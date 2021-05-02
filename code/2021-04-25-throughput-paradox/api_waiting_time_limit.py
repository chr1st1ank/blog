# Run with:
# uvicorn fastapi_main:app --workers 1 --limit-concurrency 1 --port 8080

# Test with:
# go run github.com/codesenberg/bombardier -c 4 -d 10s -l 'localhost:8080/calculate?argument=abc'
import asyncio
import concurrent
import hashlib
from collections import deque
from timeit import default_timer as timer
from uuid import uuid4 as generate_request_id

from fastapi import FastAPI, Response

app = FastAPI()


class MovingAverageEstimator:
    """Class to calculate a moving average of n observations"""
    def __init__(self, n_obervations: int=3):
        self.n_obervations = n_obervations
        self.observations = deque()

    def add_observation(self, new_time: float):
        if len(self.observations) + 1 > self.n_obervations:
            self.observations.popleft()
        self.observations.append(new_time)

    def get_estimate(self):
        if not self.observations:
            return 0
        return sum(self.observations) / len(self.observations)


class ResponseTimeLimiter:
    """Function executor with time tracking"""
    def __init__(self, n_workers):
        self.n_workers = n_workers
        self.worker_pool = concurrent.futures.ProcessPoolExecutor(max_workers=n_workers)
        self.n_active = 0
        self.last_start = timer()
        self.time_estimator = MovingAverageEstimator(3)

    def can_process_in(self, max_time):
        """Returns true if the next function call can be processed within max_time"""
        print(f"{self.n_active=}, {self.time_estimator.get_estimate()=}")
        if self.n_active >= self.n_workers:
            expected_time = self.time_estimator.get_estimate() * (self._calculations_to_await() + 1)
            print(f"{self.n_active=}, {expected_time=}")
            if expected_time > max_time:
                return False
        else:
            print(f"{self.n_active=}, expected_time={self.time_estimator.get_estimate()}")
        return True

    def _calculations_to_await(self):
        """Number of calculations until a newly arriving one would start"""
        return max(0, self.n_active / self.n_workers - 0.5)

    async def run_function(self, f, *args):
        """Call function f with the given arguments asynchronously and track the execution time."""
        loop = asyncio.get_running_loop()
        arrival_time = timer()
        queue_length = self._calculations_to_await()
        self.n_active += 1
        x = await loop.run_in_executor(self.worker_pool, f, *args)
        self.n_active -= 1
        self.time_estimator.add_observation((timer() - arrival_time) / (queue_length + 1))
        return x


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
    app.state.response_time_limiter = ResponseTimeLimiter(n_workers=1)


@app.get("/calculate")
async def get_calculate(input: str, response: Response):
    if not app.state.response_time_limiter.can_process_in(max_time=1.8):
        response.status_code = 503
        return {"error": "Too many requests"}
        
    x = await app.state.response_time_limiter.run_function(
        calculate, input, 0.5
    )

    return {"result": x}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=8088, workers=1)

