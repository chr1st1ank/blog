---
layout: post
title:  "Artificial latency"
description: How machine learning services can suprise with high latency under load.
---

**Especially compute-intensive services like a machine learning inference API can heavily suffer from queueing effects. I will demonstrate this with response time measurements of small demo service and show how to deal with this using load-shedding**

Classical web services are often I/O bound because of their database connections or source files they have to deliver. In contrast, machine learning APIs are in general heavily CPU bound. A single request on a prediction endpoint may block a CPU for as much as a second. Therefore it is vital to think about the expected load patterns and test the performance under load. If the number of clients exceeds the number of available server processes the response time can quickly explode because of the queue the requests have wait in.

## An example service
For the purpose of demonstration I wrote a very minimal API using [fastapi](https://fastapi.tiangolo.com/) with a 


## Response times under load

## Load shedding to the rescue

## Summary

