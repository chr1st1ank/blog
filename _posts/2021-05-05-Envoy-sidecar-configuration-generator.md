---
layout: post
title:  "Envoy sidecar configuration generator"
description: A configuration file generator for an envoy reverse proxy with all the bells and whistles
---

**Special issue: A configuration file generator for an envoy reverse proxy with all the bells and whistles. If you ever wanted a working base configuration with the most important features of Envoy as sidecar proxy, this is the place to get one.**

This is a follow-up for my recent post ["Getting started with an Envoy Sidecar Proxy in 5 Minutes"]({% post_url 2021-04-18-envoy-in-5-minutes %}). There I explained the basic structure of the [Envoy](https://www.envoyproxy.io) configuration file. In this special post I'm presenting a configuration file generator. It builds up on the minimal setup from the other post and adds things like authentication, encryption, rate-limiting and an optional backend connection with circuit-breaking and failover. So the main cross-cutting functionalities that have to be implemented in most micro-services. By using Envoy as sidecar all this can be left out of the application code and at the same time it is implemented robustly and efficiently.

## Envoy config file generator

{% include envoy-config-generator.html %}



Todos:
- [ ] Encryption
- [ ] Actions for rate limits
- [ ] Backend with CB


## Explanations of the individual configuration sections
### Error response sanitizing

### JWT authentication


### Rate limiting
#### Max connections
#### Leaky bucket
#### Adaptive concurrency



### Structured access log in JSON format
Envoy offers the option to write an access log in arbitrary structure. To make it indexable with log aggregators also json format is offered.

The definition used by the config generator adds a couple of fields into a JSON object, missing fields are left out (that's `omit_empty_values`) and everything is send to stderr. Of course also other log destinations are available.
```yaml
  # Structured access log in JSON format
  access_log:
  - name: envoy.access_loggers.stderr
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.access_loggers.stream.v3.StderrAccessLog
      log_format:
        json_format:
          type: "request"
          protocol: "%PROTOCOL%"
          method: "%REQ(:METHOD)%"
          path: "%REQ(:path)%"
          responseCode: "%RESPONSE_CODE%"
          duration: "%DURATION%"
          CONNECTION_TERMINATION_DETAILS: "%CONNECTION_TERMINATION_DETAILS%"
          UPSTREAM_CLUSTER: "%UPSTREAM_CLUSTER%"
          UPSTREAM_HOST: "%UPSTREAM_HOST%"
          UPSTREAM_LOCAL_ADDRESS: "%UPSTREAM_LOCAL_ADDRESS%"
          UPSTREAM_TRANSPORT_FAILURE_REASON: "%UPSTREAM_TRANSPORT_FAILURE_REASON%"
        omit_empty_values: True
```

For fine-tuning visit the documentation on [standard streams access loggers](https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/access_loggers/stream/v3/stream.proto.html?highlight=access_log) or [file access logs](https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/access_loggers/file/v3/file.proto.html?highlight=access_log).
