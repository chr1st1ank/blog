---
layout: post
title:  "Testing a Flink Stateful Function Service"
description: How to run unit tests, functional tests and load tests for an Apache Flink Stateful Function service
---
<script src="/assets/js/mermaid/8.9.3/mermaid.min.js" integrity="sha512-kxc8+BGu0/ESUMiK6Q/goKwwcoIoFVcXZ4GwMoGupMA/qTGx19BcNn1uiebOZO5f85ZD0oTdvlRKdeNh3RTnVg==" crossorigin="anonymous"></script>
<script>mermaid.initialize({startOnLoad:true, theme:"neutral"});</script>
<script src="/assets/js/plotly.js/1.58.4/plotly.min.js" integrity="sha512-odxyOOOwpEgYQnS+TzF/P33O+DfGNGqyh89pJ/u2addhMw9ZIef3M8aw/otYSgsPxLdZi3HQhlI9IiX3H5SxpA==" crossorigin="anonymous"></script>

**With [Flink Statefun](https://nightlies.apache.org/flink/flink-statefun-docs-master/) a powerful, polyglot data streaming framework has entered the real-time data processing landscape. It allows to break down a streaming pipeline into individual microservices which can each take care of one or more tasks. This post is about how to test these services.**

## Intro 
TODO: Remove heading

Classical web services are often I/O bound because of their database connections or source files they have to deliver. In contrast, machine learning APIs are in general heavily CPU bound. A single request on a prediction endpoint may block a CPU for as much as a second. Therefore it is vital to think about the expected load patterns and test the performance under load. If the number of clients exceeds the number of available server processes the response time can quickly explode because of the queue the requests have to go through. In effect the throughput decreases. The more client requests come, the fewer can actually be served.

> 
> To an outside observer, there's no difference <br>
> between "really, really slow" and "down" 
> *– Michael T. Nygard, "Release It!", p. 119*
>
## The "Greeter" example
The training project [flink-statefun-playground](flink-statefun-playground) gives us a nice example pipeline with the main structural elements of a Flink Statefun system: Ingress and egress messages, messages between functions and local state. So it is a perfect setup to show how a test framework can be set up.

The sequence diagram below shows an example of the logical flow. It starts with a kafka message containing the name of some person. The message is forwarded as HTTP request to the first stateful function ("person") by the Flink runtime. The function updates the state variable, prepares a message to the next stateful function sends both back in the HTTP response. The runtime parses the output, stores the state internally and forwards the new message to the next stateful function ("greeter") as another HTTP request. The greeter function responds with a greeting as egress message in the HTTP response. This egress message is then pushed to Kafka by the statefun runtime.

<div class="mermaid">
sequenceDiagram
    participant Kafka
    participant Flink Statefun Runtime
    participant Functions
    Kafka->>+Flink Statefun Runtime: {"name": "George"}
    Flink Statefun Runtime->>+Functions: message to "person": {"name": "George"}, state: {}
    Note right of Functions: "person" statefun
    Functions-->>-Flink Statefun Runtime: message to "greeter": {"name": "George", "visits": 1}, state: {"visits": 1}
    Flink Statefun Runtime->>+Functions: message to "greeter": {"name": "George", "visits": 1}
    Note right of Functions: "greeter" statefun
    Functions-->>-Flink Statefun Runtime: egress message: "Welcome George!"
    Flink Statefun Runtime-->>-Kafka: "Welcome George!"
</div>

So the stateful functions are normal web services with a request/response model. In addition the design is such that the functions can be completely stateless. The state is maintained by the statefun runtime. This makes it very easy to test them.

For this post we will pick the "greeter" function and show how the HTTP requests by the Flink runtime can be simulated by a normal web service test framework. This way the endpoints of the stateful function can be validated.
            
## The communication protocol of a stateful function call

The foundation for a correct application is a detailed suite of unit tests, covering all the edge cases and branches of the application logic. Stateful functions are normal web services for which the same applies. What makes this a bit harder than usual is the data flow imposed by the Statefun architecture. 

<div class="mermaid">
graph LR;
rt(Statefun Runtime) -- HTTP Post request --> API
subgraph Pod[Web Service]
API(API) -- payload --> RRH(RequestReplyHandler) --message and state--> fn(stateful function) 
end
</div>

The input of the web service is binary data coming as HTTP Post requests from the Statefun runtime. The API has to forward the payload to the RequestReplyHandler of the Flink Statefun SDK. This deserializes the data and translates it into native function calls to the actual function implementations. The code we want to test is in the API component and in the stateful function component. The other participants of a function call are provided by the framework. So we can run unit tests by mocking out the foreign parts and concentrating on either the API or the stateful function component. But how can we guarantee that it all fits together? We need an integration test, a functional test for the whole flow of the request!

If we can demystify how the payload of the HTTP request looks like, we can send HTTP requests against the web service and validate the correct handling of the whole request flow. The key to understand is a view into the [code of the RequestReplyHandler](https://github.com/apache/flink-statefun/blob/57e13b1cc3863c452b98581ba849e2103a94fe66/statefun-sdk-python/statefun/request_reply_v3.py#L231) (simplified):
```python
class RequestReplyHandler(object):
    # ...

    async def handle_async(self, request_bytes: bytes) -> bytes:
        # parse
        pb_to_function = ToFunction()
        pb_to_function.ParseFromString(request_bytes)
        # target address
        pb_target_address = pb_to_function.invocation.target
        sdk_address = sdk_address_from_pb(pb_target_address)
        
        # invoke the batch
        pb_batch = pb_to_function.invocation.invocations
        for pb_invocation in pb_batch:
            msg = Message(target_typename=sdk_address.typename, target_id=sdk_address.id,
                          typed_value=pb_invocation.argument)
            ctx._caller = sdk_address_from_pb(pb_invocation.caller)
            await fun(ctx, msg)
                
        # collect the results
        pb_from_function = collect_success(ctx)
        return pb_from_function.SerializeToString()
```

The code is a reduced to the core logic as far as we need to understand it. The input of `handle_async` is just the raw binary data from the HTTP request body. This seems to contain a protobuf object of the type `ToFunction`. It contains not only the data for a function call but also the "address", i.e. the name of the target function. One `ToFunction` object can hold the data for a whole batch of function calls as we will see later. 

The [definition of the protobufs](https://github.com/apache/flink-statefun/blob/57e13b1cc3863c452b98581ba849e2103a94fe66/statefun-sdk-protos/src/main/protobuf/sdk/request-reply.proto) used are also available in the flink-statefun repository.


## Unit testing ?

## Functional testing


## Load testing



## Summary
In this post I demonstrated why load shedding is important, especially for comparatively slow services as a machine learning API. Two approaches were outlined how one can relatively simply implement load shedding in Python, granted that an asyncio web server such as Starlette (behind FastAPI) is used.

There are of course other options for implementation, especially if you can tell a reverse proxy server in front of the service your own. Classic reverse proxies, such as Nginx or HAProxy at least allow static rate limits. These have to be tuned very carefully, though. And they don't scale automatically with your application.

But there are more sophisticated alternatives. Most notably is the approach of adaptive concurrency control. This is nicely explained in a series of blog posts by [Vikas Kumar](https://www.resilientsystems.io/2020/05/15/adaptive-concurrency-control-algorithms-part-1.html). The approach is more complicated, but it allows to have a precise dynamic rate limiting for completely unknown backend services. A reverse proxy server automatically measures the response times of the backend and adapts the maximum number of requests to it. If the backend is scaled up or down this is automatically picked up. This paradigm has also been implemented in Envoy as an experimental feature called [adaptive_concurrency_filter](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/adaptive_concurrency_filter).

The [source code for the different example services](https://github.com/chr1st1ank/blog/tree/main/code/2021-05-01-throughput-paradox) is fully available on github.



## TODOs
https://mermaid.live/
https://mermaid-js.github.io/mermaid/#/sequenceDiagram

Unit testing
https://martinfowler.com/bliki/IntegrationTest.html
Versions used