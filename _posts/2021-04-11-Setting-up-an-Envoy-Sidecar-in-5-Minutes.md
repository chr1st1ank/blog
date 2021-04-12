---
layout: post
title:  "Setting up an Envoy Proxy Sidecar in 5 Minutes"
description: A guide to getting started with Envoy as a reverse proxy sidecar container.
---
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>mermaid.initialize({startOnLoad:true, theme:"neutral"});</script>

**This post shows the basic setup of [Envoy](https://www.envoyproxy.io) as a reverse proxy in a sidecar container. It can take over all the cross-cutting networking concerns like authentication, encryption, rate-limiting, backend failover, circuit breaking and more in a robust and reusable fashion. But it is a bit hard to find a working example to start with, so here is one.**

Envoy is an extremely powerful and extendible system which can be configured statically or dynamically as part of a service mesh. This flexibility makes it hard to get started. With this post I intend to change it. It will show a typical setup of a small web API accompanied by an Envoy sidecar container which does nothing else than just forwarding requests to the backend. That's the right starting point for adding more features and experimenting with the setup.

## Example setup with docker-compose
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

If you want to test it, just get the example files from TODO: Add link and type `docker-compose up`.

## The structure of an Envoy configuration
Envoy is configured with a big, nested YAML file. It follows a very logical structure, but is very deeply nested, so that it needs some excercise to get used to it. The basic structure is as follows:

```yaml
admin:
  ...
static_resources:
  listeners:
  - ...
  clusters:
  - ...
```

There is an `admin` section which takes the configuration for Envoy's built-in admin interface. And there is the section `static_resources` for the actual configuration of its behaviour. As an alternative there would also be a section `dynamic_resources` which would define where envoy can download configuration dynamically. But that's more for a fully-fledged service mesh. We will focus on a static configuration for now.

The `static_resources` are split into the `listeners` and the `clusters` subsection. All the incoming or downstream connections and how to handle them are configured in `listeners`. This is where requests come from. The "upstream" connections are defined in `clusters`. These are the backends where Envoy forwards requests to.

## Definition of the upstream backends
Let's first look into the clusters, because that the easier part. If we detail it out for our example setup it looks like this:
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

Then there is a definition of the health checks, which is probably self-explanatory. And finally, the core of a cluster definition comes in the section `load_assignment`. This defines a single endpoint by hostname and port in this case. But it can also do load balancing with different algorithms and [many more things](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/endpoint/v3/endpoint.proto#envoy-v3-api-msg-config-endpoint-v3-clusterloadassignment). But here it is as simple as defining the port `8080` of the machine named `api` the only backend.

There are also all sorts of bells and whistles for the backend configuration. As an example I added a simple TCP connection timeout as the last point in the cluster definition.

## Listener configuration



## Configuring envoy as reverse proxy

## Further reading
A very good intro video is (https://youtu.be/D0cuv1AEftE) by Nic Jackson

Architecture overview: https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/arch_overview
Guide to envoy's backpressure: https://blog.turbinelabs.io/a-guide-to-envoys-backpressure-22eec025ef04


## Summary

With the setup described above it is possible to monitor applications running in remote kubernetes clusters with a central Prometheus instance. The official documentation about this is a bit scarce, why it took us a while to find this approach. But with the steps explained here it is very simple to set up this monitoring system in a reliable manner. I hope this helps and you spread the word.
