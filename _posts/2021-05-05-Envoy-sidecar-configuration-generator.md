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
<table>
    <legend>Features</legend>
    <tr>
        <td><input type="checkbox" id="envoy-access_log" checked></td>
        <td><label for="envoy-access_log"><a href="#structured-access-log-in-json-format">Structured access log</a>
          <br><span class="hint">JSON formatted access log messages</span>
        </label></td>
    </tr>
    <tr>
        <td><input type="checkbox" id="envoy-problem_responses" checked></td>
        <td>
          <label for="envoy-problem_responses">
            Error responses as application/problem+json 
            <br><span class="hint">Change error responses into standard problem objects as defined in https://tools.ietf.org/html/rfc7807</span>
          </label>
        </td>
    </tr>
    <tr>
        <td><input type="checkbox" id="envoy-jwt_auth" checked></td>
        <td><label for="envoy-jwt_auth">JWT authorization <a href="">⇨ more</a></label></td>
    </tr>
    <tr>
        <td><input type="checkbox" id="envoy-static_limiting" checked></td>
        <td><label for="envoy-static_limiting">Static rate limiting</label></td>
    </tr>
    <tr>
        <td><input type="checkbox" id="envoy-adaptive_concurrency" checked></td>
        <td><label for="envoy-adaptive_concurrency">Adaptive concurrency limiting</label></td>
    </tr>
    <tr>
        <td><input type="checkbox" id="envoy-backend"></td>
        <td><label for="envoy-backend">Add backend service with circuit breaker</label></td>
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
