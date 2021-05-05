---
layout: post
title:  "Getting Started with an Envoy Sidecar Proxy in 5 Minutes"
description: A guide to getting started with Envoy as a reverse proxy sidecar container.
---
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>mermaid.initialize({startOnLoad:true, theme:"neutral"});</script>

**This post shows the basic setup of [Envoy](https://www.envoyproxy.io) as a reverse proxy in a sidecar container. It will show a typical setup of a small web API accompanied by an Envoy as sidecar which does nothing else than just forwarding requests to the backend. That's the right starting point for adding more features and experimenting with the setup.** 

Envoy is an extremely powerful and extendible system which can be configured statically or dynamically as part of a service mesh. This flexibility makes it hard to get started. But when configured correctly it can take over all the cross-cutting networking concerns like authentication, encryption, rate-limiting, backend failover, circuit breaking and more. And all of it in a robust and reusable fashion without recognizable latency increase for most applications.

## Container setup with docker-compose
Let's start with the services. For the purpose of this post we will user docker-compose. But the very same can also be achieved by a Kubernetes pod with two containers or by an envoy installed into the docker container of the main application. But docker-compose is the easiest for local experiments. This is the compose file:

```yaml
version: '2.4'
services:
  envoy:
    image: envoyproxy/envoy-debug-dev:latest
    ports:
      - "8800:8800"
      - "8081:8081"
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml
  api:
    image: tiangolo/uvicorn-gunicorn-fastapi:python3.8
    command: ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
    ports:
      - "8080:8080"
    volumes:
      - ./api.py:/app/api.py
```

So here are two services. `envoy` which is our sidecar proxy and `api` which is a simplistic Python API simulating a machine learning service. The API is a small dummy service with two endpoints: `/health` and `/calculate`. The goal is to make the API only accessible through Envoy, so that we can leverage all its nice features to make the API bulletproof.

If you want to test it, just get the [example files from github](https://github.com/chr1st1ank/blog/tree/main/code/2021-04-15-envoy-in-5-minutes) and type `docker-compose up`.

## The structure of an Envoy configuration
Envoy is configured with a big, nested YAML file. It follows a very logical structure, but is very overwhelming at first, so that it needs some excercise to get used to it. The basic structure is as follows:

```yaml
admin:                # Settings for the admin interface
  ...
static_resources:
  listeners:          # Settings for incoming ("downstream") connections
  - ...
  clusters:           # Settings for outgoing ("upstream") connections
  - ...
```

There is an `admin` section which takes the configuration for Envoy's built-in admin interface. And there is the section `static_resources` for the actual configuration of its behaviour. As an alternative there would also be a section `dynamic_resources` which would define where envoy can download configuration dynamically. But that's more for a fully-fledged service mesh. We will focus on a static configuration for now.

The `static_resources` are split into the `listeners` and the `clusters` subsection. All the incoming or downstream connections and how to handle them are configured in `listeners`. This is where requests come from. The "upstream" connections are defined in `clusters`. These are the backends where Envoy forwards requests to.

## Definition of the upstream backends
Let's first look into the `clusters` section with the definition of the upstream services. If we detail it out for our example setup it looks like this:
```yaml
admin:
  ...
static_resources:
  listeners:
  - ...
  clusters:
  - name: api_backend
    type: LOGICAL_DNS
    dns_lookup_family: V4_ONLY
    health_checks:
      timeout: 0.1s
      interval: 3s
      unhealthy_threshold: 3
      healthy_threshold: 1
      http_health_check:
        path: /health
    load_assignment:
      cluster_name: api_backend
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: api
                port_value: 8080
    connect_timeout: 0.25s
``` 

There is just one element in the list of clusters here. Firstly, it has a name which we need later to refer to it. With `type` and `dns_lookup_family` it is defined how to do the DNS lookup for the backend's hostname. There are [multiple options](https://www.envoyproxy.io/docs/envoy/latest/api-v2/api/v2/cluster.proto#enum-cluster-discoverytype) and Envoy has a sophisticated strategy to look up and cache DNS names in order not to loose any time when a request comes. For our setup in docker-compose we just need a normal DNS lookup and IPv4 is sufficient.

Then there is a definition of the health checks, which is probably self-explanatory. And finally, the core of a cluster definition comes in the section `load_assignment`. This defines a single endpoint by hostname and port in this case. But it can also do load balancing with different algorithms and [many more things](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/endpoint/v3/endpoint.proto#envoy-v3-api-msg-config-endpoint-v3-clusterloadassignment). But here it is as simple as defining the port `8080` of the machine named `api`, the only backend.

There are also all sorts of bells and whistles for the backend configuration. As an example I added a simple TCP connection timeout as the last point in the cluster definition.

## Listener configuration
Now that we have our API defined as upstream service, let's look at how to expose it to the downstream side. For that we need to add a listener which gets assigned an "address". This is the hostname and port envoy should listen to. The actual functionality behind the server is defined by the key `filter_chains`. This defines a list of so called "filters" which are envoy extensions offering different functionality. 

For our simple case of an HTTP reverse proxy we need the `http_connection_manager` extension. This connection manager takes some configuration of its own. Most notably it has a `route_config` which defines the types of requests it is applicable to. By defining the wildcard domain `"*"` and accepting all routes matching the prefix `"/"` we accept all requests and send them to the cluster `api_backend`. To really activate this routing the connection manager also needs an object of the type `envoy.filters.http.router` in the key `http_filters`. Otherwise requests are accepted but not handled.

```yaml
admin:
  ...
static_resources:
  listeners:
  - address:
      socket_address:
        address: 0.0.0.0
        port_value: 8800
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          codec_type: AUTO
          stat_prefix: ingress_http
          route_config:
            name: local_route
            virtual_hosts:
              - name: local_service
                domains:
                  - "*"
                routes:
                  - match:
                      prefix: "/"
                    route:
                      cluster: api_backend
          # Don't forget: No error message but also no functionality if missing
          http_filters:
            - name: envoy.filters.http.router
              typed_config: { }
  clusters:
    ...
```

## Next steps: add functionality
The configuration above is just the basic skeleton for a reverse proxy which does basically nothing than forwarding requests to the backend. It becomes interesting when we add more functionality. For a web application there are a couple of things envoy can handle which you would have to implement in application code otherwise:

- Authorization: Use e.g. JWT authentication or HTTP basic authentication
- Encryption: Add TLS encryption
- Rate limiting and load shedding: Cut off spikes in request volume
- Internal retries

If the webservice has backends itself (e.g. a database) there are more useful things, e.g.:
- Circuit breaking
- Failover
- Client side load balancing

These things can all be plugged in as additional configuration options. You may follow the many examples of the [official documentation](https://www.envoyproxy.io/docs/envoy/latest/). With a working setup as a starting point this should be no longer a problem.

## Summary and further reading

I hope the explanations help a bit to demystify how envoy is configured. Envoy's flexibility comes for the price of complexity in the configuration. But I believe with a working example and some explanations one can go up the learning curve quite steeply. The key points are to distinguish between the "listener" and "clusters" section and to understand the idea of "filters" as a chain of plugins which are used to process a request step by step.
The complete [source code is available on github](https://github.com/chr1st1ank/blog/tree/main/code/2021-04-15-envoy-in-5-minutes) for easier access.

If you'd like to get it explained verbally I can recommend a very good [intro video by Nic Jackson](https://youtu.be/D0cuv1AEftE).
If you want to get a quick overview of useful features, there is TR Jordan's [Guide to envoy's backpressure](https://blog.turbinelabs.io/a-guide-to-envoys-backpressure-22eec025ef04). And at last it is definitely also a good idea to read the official [Architecture overview](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/arch_overview) in the envoy documentation.
