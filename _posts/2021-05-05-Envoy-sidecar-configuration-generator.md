---
layout: post
title:  "Envoy sidecar configuration generator"
description: A configuration file generator for an envoy reverse proxy with all the bells and whistles
---

**Special issue: A configuration file generator for an envoy reverse proxy with all the bells and whistles. If you ever wanted a working base configuration with the most important features of Envoy as sidecar proxy, this is the place to get one.**

This is a follow-up for my recent post ["Getting started with an Envoy Sidecar Proxy in 5 Minutes"]({% post_url 2021-04-18-envoy-in-5-minutes %}). There I explained the basic structure of the [Envoy](https://www.envoyproxy.io) configuration file. In this special post I'm presenting a configuration file generator. It builds up on the minimal setup from the other post and adds things like authentication, encryption, rate-limiting and an optional backend connection with circuit-breaking and failover. So the main cross-cutting functionalities that have to be implemented in most micro-services. By using Envoy as sidecar all this can be left out of the application code and at the same time it is implemented robustly and efficiently.

## Envoy config file generator

{% include envoy-sidecar-configuration-generator.html %}

Choose the features of the envoy proxy with the checkboxes below. The detailed configuration, e.g. of hostnames, ports or limits can be done in the yaml file afterwards.

Follow the links in the checkbox descriptions to get further explanations on the individual settings.
<div id="template-inputs">
<fieldset>
<legend>Features</legend>
<table>
    <tr>
        <td><input type="checkbox" id="envoy-access_log" checked></td>
        <td><label for="envoy-access_log">
          <a href="#structured-access-log-in-json-format">Structured access log</a><br>
          <span class="hint">JSON formatted access log messages</span>
        </label></td>
    </tr>
    <tr>
        <td><input type="checkbox" id="envoy-problem_responses" checked></td>
        <td><label for="envoy-problem_responses">
          <a href="#standard-json-error-responses">Standard JSON error responses</a><br>
          <span class="hint">Change error responses into standard application/problem+json objects</span>
        </label></td>
    </tr>
    <tr>
        <td><input type="checkbox" id="envoy-jwt_auth"></td>
        <td><label for="envoy-jwt_auth">
          <a href="#jwt-authorization">JWT authorization</a><br>
          <span class="hint">Use JSON Web Tokens to verify requests are legitimate</span>
        </label></td>
    </tr>
    <tr>
        <td><input type="checkbox" id="envoy-tls_termination"></td>
        <td><label for="envoy-tls_termination">
          <a href="#tls-termination">TLS termination</a><br>
          <span class="hint">Expose service with TLS encryption</span>
        </label></td>
    </tr>
    <tr>
        <td><input type="checkbox" id="envoy-static_limiting" checked></td>
        <td><label for="envoy-static_limiting">
          <a href="#token-bucket-rate-limiting">Static rate limiting</a><br>
          <span class="hint">Enable static rate limiting with the token-bucket method</span>
        </label></td>
    </tr>
    <tr>
        <td><input type="checkbox" id="envoy-adaptive_concurrency" checked></td>
        <td><label for="envoy-adaptive_concurrency">
          <a href="#adaptive-concurrency-limiting">Adaptive concurrency limiting</a><br>
          <span class="hint">Dynamic rate limiting with a gradient method</span>
        </label></td>
    </tr>
    <tr>
        <td><input type="checkbox" id="envoy-backend"></td>
        <td><label for="envoy-backend">
          <a href="#external-backend-services">Add a backend service</a><br>
          <span class="hint">Add a backend service with TLS encryption and circuit breaker</span>
        </label></td>
    </tr>
</table>
</fieldset>
</div>

Generated `envoy.yaml` configuration file:
<div class="highlight">
<button class="btn" id="config-select-btn" style="float: right;">Select all</button>
<button class="btn" id="config-copy-btn" style="float: right;">Copy to clipboard</button>
<pre style="height: 30em">
<code id="envoy-config">
TEMPLATE
</code>
</pre>
</div>

## Structured access log in JSON format
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

This is an example log message generated by the configuration above (pretty-printed on multiple lines to make it better readable):
```json
{
  "type": "request",
  "method": "GET",
  "protocol": "HTTP/1.1",
  "path": "/health",
  "duration": 1,
  "UPSTREAM_CLUSTER": "api_cluster",
  "UPSTREAM_LOCAL_ADDRESS": "172.20.0.3:36014",
  "responseCode": 200,
  "UPSTREAM_HOST": "172.20.0.2:9000"
}
```

For fine-tuning visit the documentation on [standard streams access loggers](https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/access_loggers/stream/v3/stream.proto.html?highlight=access_log) or [file access logs](https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/access_loggers/file/v3/file.proto.html?highlight=access_log).

## Standard JSON error responses
With a `local_reply_config` in the filter chain of an `http_connection_manager` one can fine-tune HTTP responses before they go to the downstream services. This is a real [OSI layer 7](https://en.wikipedia.org/wiki/Application_layer) feature. That means Envoy has to process the full HTTP message instead of forwarding the raw TCP packets. But this is the discipline Envoy shines in.
```yaml
   local_reply_config:
            mappers:
              - filter:
                  status_code_filter:
                    comparison:
                      op: EQ
                      value:
                        default_value: 429
                        runtime_key: key_b
                body_format_override:
                  json_format:
                    status: "%RESPONSE_CODE%"
                    title: "Too many requests"
                    detail: "%LOCAL_REPLY_BODY%"
                    type: "about:blank"
                  content_type: "application/problem+json"
              - filter:
                  status_code_filter:
                    comparison:
                      op: GE
                      value:
                        default_value: 400
                        runtime_key: key_b
                body_format_override:
                  json_format:
                    status: "%RESPONSE_CODE%"
                    title: "Error %RESPONSE_CODE%"
                    detail: "%LOCAL_REPLY_BODY%"
                    type: "about:blank"
                  content_type: "application/problem+json"
```

This compares the HTTP status code of the upstream HTTP responses to certain values and wraps the response body into a json message with the content type "application/problem+json". The benefit is that the message conforms to a well-known standard (https://tools.ietf.org/html/rfc7807) and is more easily machine-readable than a plain-text message.

The same mechanism is also used to define a proper response in case the local rate limiting hits and returns status code 429.

An example response (with HTTP status code 401) would look like this:
```json
{"type":"about:blank","status":401,"detail":"Jwt is missing","title":"Error 401"}
```

The options and available template variables can be found in [Envoy's documentation about the LocalReplyConfig object](https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/filters/network/http_connection_manager/v3/http_connection_manager.proto.html?highlight=local_reply_config#extensions-filters-network-http-connection-manager-v3-localreplyconfig).


## JWT Authorization

This uses the [JWT http filter](https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/filters/http/jwt_authn/v3/config.proto.html?highlight=local_jwks#jwt-authentication) to do validation of JWT tokens before requests are related to the upstream backends. This is the filter that's added to the `http_filters` section:

```python
- name: envoy.filters.http.jwt_authn
  typed_config:
    "@type": type.googleapis.com/envoy.extensions.filters.http.jwt_authn.v3.JwtAuthentication
    providers:
        provider1:
          issuer: issuer1
          audiences:
          - audience1
          - audience2
          remote_jwks:
            http_uri:
              uri: https://example.com/.well-known/jwks.json
              cluster: example_jwks_cluster
              timeout: 1s
        provider2:
          issuer: "issuer2"
          audiences:
            - www.example.com
          local_jwks:
            filename: /etc/envoy/public.jwks
    rules:
      # Not jwt verification for /health path
      - match:
          prefix: /health
      # Verification for either provider1 or provider2 is required for all other requests
      - match:
          prefix: /
        requires:
          requires_any:
            requirements:
            - provider_name: provider1
            - provider_name: provider2
```

This configuration is already more sophisticated to show the flexibility of the implementation. There are two types of tokens: one type issued by some service at www.example.com, another one where the public key is only available as local file.
And there are two types of endpoints: the `/health` endpoint skips any authentication and all the other endpoints are accessible with a valid JWT of any of the two types.
This degree of flexibility is usually only available for full-fledged API gateways or it requires a custom implementation in the application code. Envoy offers it out-of-the-box, rock-solid and very fast.

The key format used here (JWK) is well-documented at [auth0.com](https://auth0.com/docs/tokens/json-web-tokens/json-web-key-sets). For testing there are plenty of online tools available. One of them which I'd like to mention is [jwt.io](https://jwt.io) which offers online decoding and verification of tokens. Out of principle such tools should of course only be entrusted with test credentials.

## TLS termination
As one of the standard features of a reverse proxy also Envoy offers [TLS encryption](https://www.envoyproxy.io/docs/envoy/latest/start/quick-start/securing#upstream-and-downstream-tls-contexts) of connections.
The configuration used here is directly taken from the [examples in Envoy's documentation](https://www.envoyproxy.io/docs/envoy/latest/start/sandboxes/tls) and need to be adapted to the use case.

## Rate limiting

With the two options for rate-limiting shown here I tried to implement two ways of rate-limiting similar to what I showed in ["The Throughput Paradox – Why a Machine Learning API Needs Load Shedding"]({% post_url 2021-05-02-throughput-paradox %}). Unfortunately the semaphore algorithm used as a first variant in the article is not available. But it is possible to achieve a similar effect with a well-configured token bucket configuration in Envoy. In my post I offered a dynamic limiting based on measured response times and the information about the number of available workers. Envoy offers an implementation of a gradient based approach which is less precise but more flexible in that it doesn't need specific information about the backend.

Go with what you deem more suitable for your use-case, but I would advise to use some solution for load shedding to keep response times low.

### Token bucket rate limiting
[Token bucket rate limiting](https://en.wikipedia.org/wiki/Token_bucket) means that every n seconds a number of tokens is added to a "bucket". If this bucket reaches its maximum capacity no more tokens are added (the bucket spills over). Every request that approaches the service needs to take one token out of the bucket to proceed. If no more tokens are available the request is rejected. This allows a short burst of requests but in general sets a fixed rate limit.

To achieve this in Envoy one can use so-called "local rate limiting" which needs definitions in three places. First the routes to guard get the configuration of the [local rate limit in the input filter chain](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/local_rate_limit_filter#config-http-filters-local-rate-limit-descriptors):
```yaml
typed_per_filter_config:
  envoy.filters.http.local_ratelimit:
    "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
    stat_prefix: http_local_rate_limiter
    token_bucket:
      max_tokens: 2
      tokens_per_fill: 2
      fill_interval: 1s
    filter_enabled:
      default_value:
        numerator: 100
        denominator: HUNDRED
    filter_enforced:
      default_value:
        numerator: 100
        denominator: HUNDRED
    response_headers_to_add:
      - append: false
        header:
          key: x-local-rate-limit
          value: 'true'
```

This defines a token bucket which gets just 2 new tokens per second (please adjust to your needs). With `filter_enabled` and `filter_enforced` one can define how much of the load should be dropped in case of overload.

In order for this to have any effect it is also necessary to add the following section to the `http_filters` chain:
```yaml
- name: envoy.filters.http.local_ratelimit
  typed_config:
    "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
    stat_prefix: http_local_rate_limiter
```

Finally it is also necessary to define the desired action of the rate limiting. For that
```yaml
rate_limits:
- actions:
  - request_headers:
      header_name: x-envoy-downstream-service-cluster
      descriptor_key: client_cluster
  - request_headers:
      header_name: ":path"
      descriptor_key: path
```

The local rate limit makes Envoy return status code 429 errors if the limit is reached:
```json
{"type":"about:blank","title":"Too many requests","detail":"local_rate_limited","status":429}
```

### Adaptive concurrency limiting
The [adaptive concurrency limit](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/adaptive_concurrency_filter.html?highlight=adaptive) is an implementation of Netflix' gradient algorithm (see [netflixtechblog](https://netflixtechblog.medium.com/performance-under-load-3e6fa9a60581)).

Although the algorithm is designed for rate limiting without manual configuration, it offers a lot of parameters:
```yaml
- name: envoy.filters.http.adaptive_concurrency
  typed_config:
    "@type": type.googleapis.com/envoy.extensions.filters.http.adaptive_concurrency.v3.AdaptiveConcurrency
    gradient_controller_config:
      sample_aggregate_percentile:
        value: 50
      concurrency_limit_params:
        concurrency_update_interval: 0.1s
        max_concurrency_limit: 100
      min_rtt_calc_params:
        jitter:
          value: 1
        buffer:
          value: 1
        interval: 30s
        request_count: 10
        min_concurrency: 3
    enabled:
      default_value: true
      runtime_key: "adaptive_concurrency.enabled"
```

The main idea is, that there is a "gradient" which is calculated from the minimum response time under low load and the current actual response time:

gradient = minResponseTime / currentResponseTime

The new concurrency limit is then calculated from the old limit multiplied by the gradient and with some fixed value "headroom" added:

newLimit = oldLimit · gradient + headroom

This is a bit simplified as also the many parameters might indicate, but it explains the main idea. Most important with regards to configuration are the two hard limits `max_concurrency_limit` and `min_concurrency` which set upper and lower bounds for the number of parallel requests which are permitted. My experiments showed that the dynamic limit can grow under a constant low load to very high values. This has the effect that an overload situation is not handled immediately because the limit is only gradually decreased again. So one should set the max value not too high.

With this kind of rate limiting envoy returns an error with status code 503 if the service is overloaded:
```json
{"type":"about:blank","detail":"reached concurrency limit","title":"Error 503","status":503}
```

## External backend services
In a situation where a service relies on some upstream service, this can also be handled by the same sidecar proxy.
To handle these upstream dependency another listener address with minimal http filter is added, pointing to an additional cluster definition:

```yaml
- address:
    socket_address:
      address: 0.0.0.0
      port_value: 10000
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
          - name: backend_app
            domains:
            - "*"
            routes:
            - match:
                prefix: "/"
              route:
                cluster: backend_cluster
        http_filters:
        - name: envoy.filters.http.router
clusters:
- name: backend_cluster
  connect_timeout: 0.5s
  type: STRICT_DNS
  health_checks:
    always_log_health_check_failures: true
    timeout: 0.1s
    interval: 3s
    unhealthy_threshold: 3
    healthy_threshold: 1
    http_health_check:
      path: /
  circuit_breakers:
    thresholds:
    - priority: "DEFAULT"
      max_requests: 75
      max_pending_requests: 35
      retry_budget:
        min_retry_concurrency: 1
  load_assignment:
    cluster_name: backend_cluster
    endpoints:
    - lb_endpoints:
      - endpoint:
          address:
            socket_address:
              address: www.w3.org
              port_value: 443
  # Enable TLS encryption
  transport_socket:
    name: envoy.transport_sockets.tls
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.UpstreamTlsContext
```

The advantage is that envoy now takes care of active health checking and also adds a [circuit breaker functionality](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_circuit_breakers). That means that a failing backend is completely cut off until it becomes available again. Neither the backend needs to fear a lot of retries nor the downstream service (our webservice) needs to wait until the requests maybe time out eventually.

If multiple backends are available they can simply be added to the `ln_endpoints` section and Envoy automatically handles load balancing and fails over to the remaining backend if one is down.

## Summary

