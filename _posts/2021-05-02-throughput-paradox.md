---
layout: post
title:  "The Throughput Paradox – Why a Machine Learning API Needs Load Shedding"
description: Why throughput decreases and latency increases under load in a simple machine learning API.
---
<script src="/assets/js/plotly.js/1.58.4/plotly.min.js" integrity="sha512-odxyOOOwpEgYQnS+TzF/P33O+DfGNGqyh89pJ/u2addhMw9ZIef3M8aw/otYSgsPxLdZi3HQhlI9IiX3H5SxpA==" crossorigin="anonymous"></script>

**Especially compute-intensive services like a machine learning inference API can heavily suffer from queueing effects. I will demonstrate this with response time measurements of small demo service and show how to deal with this using load-shedding**

Classical web services are often I/O bound because of their database connections or source files they have to deliver. In contrast, machine learning APIs are in general heavily CPU bound. A single request on a prediction endpoint may block a CPU for as much as a second. Therefore it is vital to think about the expected load patterns and test the performance under load. If the number of clients exceeds the number of available server processes the response time can quickly explode because of the queue the requests have to go through. In effect the throughput decreases. The more client requests come, the fewer can actually be served.

> 
> To an outside observer, there's no difference <br>
> between "really, really slow" and "down" 
> *– Michael T. Nygard, "Release It!", p. 119*
>

## An example service
In order to demonstrate the effect we can create a small demo service in Python using [fastapi](https://fastapi.tiangolo.com/):
```python
import asyncio
import concurrent

from fastapi import FastAPI, Response

import hashlib
from timeit import default_timer as timer

app = FastAPI()

def calculate(input: str, timeout=5.0):
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

@app.on_event("shutdown")
async def on_shutdown():
    app.state.pool.shutdown()

@app.get("/calculate-limited")
async def get_calculate_limited(argument: str, response: Response):
    if app.state.semaphore.locked():
        response.status_code = 503
        return {"error": "Too many requests"}
    async with app.state.semaphore:
        loop = asyncio.get_running_loop()
        x = await loop.run_in_executor(app.state.pool, calculate, argument, 0.5)
        return {"result": x}

@app.get("/calculate")
async def get_calculate(argument: str):
    x = calculate(argument, 5)
    return {"result": x}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=8088, workers=1, backlog=4)

```

This is the wire frame of a typical though very minimal machine learning prediction API. In order to focus on the actual topic the actual machine learning model is replaced here by the function `calculate()`. It simply keeps the CPU busy for a certain amount of time just by calculating hash sums of the input string. The specialty of a machine learning model is that it does just that. It doesn't read files or call backend services, but just loads the CPU (or GPU) with instructions.

Note that the example services has a constant and deterministic processing time of about 500ms, because that's how long the `calculate()` function keeps running.

That means the maximum throughput of the service is 1/500ms = 2/s.

## Response times under load
Now let's analyze the behaviour of such a service under load. For this purpose we use [bombardier](https://github.com/codesenberg/bombardier), a very simple but extremely fast and easy to handle load testing tool.

Start the API:
```shell
> python api.py
INFO:     Started server process [324095]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8088 (Press CTRL+C to quit)
```

Do a single request:
```shell
> curl 'localhost:8088/calculate?input=test'
{"result":"66d4582f0282176dba7650ee1805e8cbfed5511c42f5de920722b9503da11754"}
```

Do a load test for 30 seconds with just one client and a request timeout of 2 seconds:
```shell
> bombardier -c 1 -t 2s -d 30s --latencies 'localhost:8088/calculate?input=test'
Bombarding http://localhost:8088/calculate?input=test for 30s using 1 connection(s)
[==========================================================================================] 30s
Done!
Statistics        Avg      Stdev        Max
  Reqs/sec         1.97       9.52      57.37
  Latency      501.45ms     1.12ms   508.72ms
  Latency Distribution (Total)
     50%   501.20ms
     75%   501.26ms
     90%   501.40ms
     95%   501.86ms
     99%   504.98ms
  Latency Distribution (2xx)
     50%   501.20ms
     75%   501.26ms
     90%   501.40ms
     95%   501.86ms
     99%   504.98ms
  HTTP codes:
    1xx - 0, 2xx - 60, 3xx - 0, 4xx - 0, 5xx - 0
    others - 0
  Throughput:     566.33/s
```

So we see what we would expect. The response time is at around 500ms and no request runs into the defined timeout of two seconds.

Now let's examine what happens if we suddenly get many requests. This is the result with four clients:
```shell
> bombardier -c 4 -t 2s -d 30s --latencies 'localhost:8088/calculate?input=test'
Bombarding http://localhost:8088/calculate?input=test for 30s using 4 connection(s)
[==========================================================================================] 30s
Done!
Statistics        Avg      Stdev        Max
  Reqs/sec         0.33       5.73     100.46
  Latency         8.72s      3.11s     10.01s
  Latency Distribution (Total)
     50%     10.01s
     75%     10.01s
     90%     10.01s
     95%     10.01s
     99%     10.01s
  Latency Distribution (2xx)
     50%      1.01s
     75%      1.01s
     90%      1.01s
     95%      1.01s
     99%      1.01s
  HTTP codes:
    1xx - 0, 2xx - 2, 3xx - 0, 4xx - 0, 5xx - 0
    others - 12
  Errors:
       timeout - 12
  Throughput:     176.89/s
```

We see the effect of a queue which forms up in front of the service. The API has only one worker process, so it can only handle one client at a time. Every client has to wait until three other clients in front of him have been served. Once he gets his result and returns with the next request, the other three clients are already back in front of him. 

This is what we could also take from [Little's law](https://en.wikipedia.org/wiki/Little%27s_law):

Average processing time = Average clients in the system / throughput

So with four clients and without timeouts we would see:

Average processing time = 4 / 2/s = 2s

This is not a theoretic problem. It happens in practice very fast because production load is not constant at all but rather very dynamic with a lot of spikes. In such situations the problem is even worse than here. In our setup we have a constant number of clients which wait in line. So the (re-)arrival rate equals the processing rate, so that the queue length is constant. In production you may observe situations where the arrival rate is higher than the processing rate, so that the queue grows towards infinity.

On client side there is typically some timeout our service cannot be aware about. If a client times out and aborts the request he cannot tell the API about it. So the API will even process requests when the client has long since stopped listening.

The following chart shows the development of response times and throughput depending on the number of clients:
<div id="chart-unrestricted-api"  style="width:80%;"></div>
<script>
var throughput = {
  x: [1, 2, 3, 4, 5],
  y: [1.97, 1.96, 1.93, 1.95, 1.93],
  type: 'scatter',
  name: 'Throughput (without timeout, req/s)'
};
var throughputTimeout = {
  x: [1, 2, 3, 4, 5],
  y: [1.97, 1.96, 1.93, 0.37, 0.37],
  type: 'scatter',
  name: 'Throughput (successful requests at 2s timeout, req/s)'
};
var responseTime = {
  x: [1, 2, 3, 4, 5],
  y: [0.501, 1.00, 1.49, 2.00, 2.50],
  type: 'scatter',
  name: 'Response time of successful requests (p50 in s)',
  secondary_y: true
};
var data = [responseTime, throughputTimeout, throughput];
var layout = {
  title: 'Throughput and response times',
  xaxis: {
    title: 'Clients',
    showgrid: false,
    zeroline: false,
    nticks: 5
  }
};
var options = {displayModeBar: false}
Plotly.newPlot(document.getElementById('chart-unrestricted-api'), data, layout, options);
</script>

We can see that the response time increases linearly with the number of concurrent clients. The throughput from server perspective is always the same. But the throughput from the perspective of a client with timeout drops to zero as soon as the response time is above the timeout threshold. This means that the service is practically offline although it is processing requests at full speed.

## Load shedding to the rescue
One of the very few options the API has to handle the situation is "load shedding". This means it can serve as many requests as possible and dismiss the others immediately instead of creating a long queue.

To achieve this in Python we need a subprocess for the blocking calculation, so that the main process can manage a queue and reject connections if necessary.
### Option 1: Limited queue length
The first option to solve this is an explicit queue with limited length. 

The solution uses asyncio to enable the server to work on multiple concurrent requests at the same time.

To model the queue an `asyncio.Semaphore` object  can be used. This kind of object serves as context manager in an `async with` statement. Only a certain number of coroutines are allowed to be inside the `with` block at the same time. The others are blocked waiting. In the actual API endpoint we can use the semaphore's `locked()` function to check if the queue is already full. In this case we can immediately return an error code to the client. In all other cases we can continue to start the calculation in a subprocess.

The actual executions can be done in a ProcessPoolExecutor, so that the main process is able to handle more requests. This has the nice side effect that we could also use multiple workers to achieve a higher throughput on multiple CPUs if we whished to. 

Both objects, the `Semaphore` and the `ProcessPoolExecutor` are initialized in the `on_startup()` function which is executed on application startup. The objects are stored in the `app.state` attribute. As asyncio is single-threaded we don't have to worry about thread-safety here.

```python
import asyncio
import concurrent
import hashlib
from timeit import default_timer as timer

from fastapi import FastAPI, Response

app = FastAPI()


def calculate(input: str, timeout=0.5):
    # unchanged...

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
```

If we run a performance test on this now we can see that not a single request runs into a timeout anymore. The successful requests are processed within a reasonable time and the others get a 503 error immediately:
```shell
> bombardier -c 4 -d 30s -t 2s --latencies 'localhost:8088/calculate?input=test'
Bombarding http://localhost:8088/calculate?input=test for 30s using 4 connection(s)
[==========================================================================================] 30s
Done!
Statistics        Avg      Stdev        Max
  Reqs/sec      1763.46     336.97    2278.46
  Latency        2.27ms    33.45ms      1.01s
  Latency Distribution (Total)
     50%     0.98ms
     75%     1.15ms
     90%     1.40ms
     95%     1.69ms
     99%     3.10ms
  Latency Distribution (2xx)
     50%      1.00s
     75%      1.00s
     90%      1.00s
     95%      1.00s
     99%      1.01s
  HTTP codes:
    1xx - 0, 2xx - 61, 3xx - 0, 4xx - 0, 5xx - 52881
    others - 0
  Throughput:   428.57KB/s
```

The following chart shows the development of response times and throughput depending on the number of clients:
<div id="chart-queue-limit"  style="width:80%;"></div>
<script>
var throughput = {
  x: [1, 2, 3, 4, 5],
  y: [2.00, 2.03, 2.03, 2.03, 2.03],
  type: 'scatter',
  name: 'Throughput (successful requests, req/s)'
};
var responseTime = {
  x: [1, 2, 3, 4, 5],
  y: [0.503, 1.00, 1.00, 1.00, 0.99],
  type: 'scatter',
  name: 'Response time of successful requests (p50 in s)',
  secondary_y: true
};
var data = [responseTime, throughput];
var layout = {
  title: 'Throughput and response times with limited queue',
  xaxis: {
    title: 'Clients',
    showgrid: false,
    zeroline: false,
    nticks: 5
  }
};
var options = {displayModeBar: false}
Plotly.newPlot(document.getElementById('chart-queue-limit'), data, layout, options);
</script>

So that's just what we want. Under overload our service stays reactive and keeps serving as many requests as possible. But load which exceed the capacity is directly refused, so that the client application doesn't have to wait unnecessarily and the response time stays low.

### Option 2: Limited response time
The approach above is very effective. The only disadvantage is that we can only set a specific queue length, we cannot define a certain target response time. In our case this would be beneficial, though. Because we know what response time is acceptable by our client and so we could try to enqueue just as many requests as could be served in time. In a dynamic situation with a temporary peak of requests such a queue would optimize the service's availability.

This is also not much more complicated. One approach is to track the response times and the queue length so that the response time for every new request can be estimated. Based on this estimate the API can decide whether a request should be added to the queue or refused because it is bound to run into the timeout.

The following listing introduces `MovingAverageEstimator`, a small class which tracks the last few observed times in a deque container. The average of these observations is then provided as estimate. Another small class introduced is `ResponseTimeLimiter`, a wrapper around the `ProcessPoolExecutor` we already had before. This replaces the Semaphore. The `ResponseTimeLimiter` measures the response times and the queue length, so that it can always tell if the next function call would be processed within a certain maximum time or not.

```python
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
    # unchanged

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
```

The endpoint function `get_calculate` now uses the `ResponseTimeLimiter` to decide whether to refuse the request if it can't be processed within a certain time. Here we set the limit at 1.8s to aim just below the client timeout of 2s.

The performance tests show a similar result to the simpler load shedding implementation. Now the latency under overload is 1.5s for the successful requests, because we set the limit of 1.8s. The full theoretic maximum of ~60 requests are served in the 30s period of the tests and many other requests were refused with a 503 error very quickly:
```shell
> bombardier -c 4 -d 30s -t 2s --latencies 'localhost:8088/calculate?input=test'
Bombarding http://localhost:8088/calculate?input=test for 30s using 4 connection(s)
[==========================================================================================] 30s
Done!
Statistics        Avg      Stdev        Max
  Reqs/sec      1571.98     197.90    1853.91
  Latency        2.57ms    53.71ms      1.51s
  Latency Distribution (Total)
     50%   599.00us
     75%   636.00us
     90%   688.00us
     95%   743.00us
     99%     1.19ms
  Latency Distribution (2xx)
     50%      1.50s
     75%      1.50s
     90%      1.50s
     95%      1.50s
     99%      1.51s
  HTTP codes:
    1xx - 0, 2xx - 62, 3xx - 0, 4xx - 0, 5xx - 47128
    others - 0
  Throughput:   375.85KB/s
```

The following diagram shows again the throughput and response times by the number of clients:
<div id="chart-time-limit"  style="width:80%;"></div>
<script>
var throughput = {
  x: [1, 2, 3, 4, 5],
  y: [2.00, 2.03, 2.07, 2.07, 2.07],
  type: 'scatter',
  name: 'Throughput (successful requests, req/s)'
};
var responseTime = {
  x: [1, 2, 3, 4, 5],
  y: [0.503, 1.00, 1.50, 1.5, 1.5],
  type: 'scatter',
  name: 'Response time of successful requests (p50 in s)',
  secondary_y: true
};
var data = [responseTime, throughput];
var layout = {
  title: 'Throughput and response times with limited queue',
  xaxis: {
    title: 'Clients',
    showgrid: false,
    zeroline: false,
    nticks: 5
  }
};
var options = {displayModeBar: false}
Plotly.newPlot(document.getElementById('chart-time-limit'), data, layout, options);
</script>

## Summary
In this post I demonstrated why load shedding is important, especially for comparatively slow services as a machine learning API. Two approaches were outlined how one can relatively simply implement load shedding in Python, granted that an asyncio web server such as Starlette (behind FastAPI) is used.

There are of course other options for implementation, especially if you can tell a reverse proxy server in front of the service your own. Classic reverse proxies, such as Nginx or HAProxy at least allow static rate limits. These have to be tuned very carefully, though. And they don't scale automatically with your application.

But there are more sophisticated alternatives. Most notably is the approach of adaptive concurrency control. This is nicely explained in a series of blog posts by [Vikas Kumar](https://www.resilientsystems.io/2020/05/15/adaptive-concurrency-control-algorithms-part-1.html). The approach is more complicated, but it allows to have a precise dynamic rate limiting for completely unknown backend services. A reverse proxy server automatically measures the response times of the backend and adapts the maximum number of requests to it. If the backend is scaled up or down this is automatically picked up. This paradigm has also been implemented in Envoy as an experimental feature called [adaptive_concurrency_filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/adaptive_concurrency_filter).

The [source code for the different example services](https://github.com/chr1st1ank/blog/tree/main/code/2021-05-01-throughput-paradox) is fully available on github.
