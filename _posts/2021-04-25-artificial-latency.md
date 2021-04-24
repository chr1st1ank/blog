---
layout: post
title:  "Artificial latency"
description: How machine learning services can suprise with high latency under load.
---

**Especially compute-intensive services like a machine learning inference API can heavily suffer from queueing effects. I will demonstrate this with response time measurements of small demo service and show how to deal with this using load-shedding**

Classical web services are often I/O bound because of their database connections or source files they have to deliver. In contrast, machine learning APIs are in general heavily CPU bound. A single request on a prediction endpoint may block a CPU for as much as a second. Therefore it is vital to think about the expected load patterns and test the performance under load. If the number of clients exceeds the number of available server processes the response time can quickly explode because of the queue the requests have wait in.

> The net ersult is lenghtening response times until callers start timing out. 
> To an outside observer, there's no difference between "really, really slow" and "down"
> 
> *Michael T. Nygard, Release It!, p. 119

## An example service
In order to demonstrate the effect we can quickly create a small demo service in Python using [fastapi](https://fastapi.tiangolo.com/):
```python
# TODO: Add health endpoint
```

This is the wireframe of a typical though very minimalistic machine learning prediction API. In order to focus on the actual topic the actual machine learning model is replaced here by the function `calculate()`. It simply keeps the CPU busy for a certain amount of time just by calculating hash sums of the input string. The specialty of a machine learning model is that it does just that. It doesn't read files or call backend services, but just loads the CPU (or GPU) with instructions.

Note that the example services has a constant and deterministic processing time of about 500ms, because that's how long the `calculate()` function keeps running.

## Response times under load
Now let's analyze the behaviour of such a service under load. For this purpose we use [bombardier](https://github.com/codesenberg/bombardier), a very simplistic but extremely fast and easy to handle load testing tool.

Start the API:
```shell
# python api.py
# TODO: Output
```

Do a single request:
```shell
# curl localhost:8088/calculate?input=test
# TODO: OUtput
```

Do a load test with just one client thread:
```shell
# bombardier -c 1 -t 2s -d 30s localhost:8088/calculate?input=test
# TODO: OUtput
```

So we see what we would expect. The reponse time is at around 500ms, no request runs into the defined timeout of two seconds.

Now let's see what happens if we suddenly get many requests. Let's try with five clients which try to get results:
```shell
# bombardier -c 5 -t 2s -d 30s localhost:8088/calculate?input=test
# TODO: OUtput
```

Now we see the effect of the queue which forms up in front of the service. The API has only one worker process, so it can only handle one client at a time. Every client has to wait until four other clients in front of him have been served. Once he gets his result and returns with the next request, the other four clients are already back in front of him. 

This is not a theoretic problem. It happens in practice very fast because production load is not constant at all but rather very dynamic with a lot of spikes. In such situations the problem is even worse than here. In our setup we have a constant number of clients which wait in line. So the arrival rate equals the processing rate, so that the queue length is constant. In production you may observe situations where the arrival rate is higher than the processing rate, so that the queue grows towards infinity.

Because on client side there is typically some timeout our API does not know about. If a client times out and aborts the request he cannot tell the API about it. So the API will even process requests when the client has long since stopped listening.

The following chart shows the development of response times and the ratio of timeouts depending on the number of clients:
# TODO: add chart

## Load shedding to the rescue
One of the very few options the API has to handle the situation is load shedding. This means it can serve as many requests as possible and refuse the others immediately instead of creating a queue.

To achieve this in Python we need a subprocess for the blocking calculation, so that the main process can manage a queue and reject connections if necessary.
```python
# TODO: Implementation with load shedding
```

We use a process pool for the calculation subprocess and a semaphore object...

## Summary

