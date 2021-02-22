---
layout: post
title:  "Multicluster Application Monitoring with Prometheus"
description: How to centralize the monitoring of Kubernetes applications running in different environments with Prometheus.
---
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>mermaid.initialize({startOnLoad:true, theme:"neutral"});</script>

**[Prometheus](https://prometheus.io/) is a popular choice for application monitoring. It is easy to set up and can be deployed alongside the applications inside a Kubernetes cluster. However, when you cannot run your main Prometheus instance within the same cluster it becomes a bit more tricky. At work we recently set up Prometheus monitoring for a web service which is deployed to independent kubernetes clusters in different regions. The official documentation is a bit sparce on this topic. In this post I will show what I learned about combining the metrics of applications running in separate Kubernetes clusters.**

In contrast to other monitoring systems, Prometheus follows a pull workflow. The monitoring targets have to expose their metrics on an HTTP endpoint where Prometheus can "scrape" the data at its own pace. This is typically done by modules called ["exporters"](https://prometheus.io/docs/instrumenting/exporters/), e.g. the "node exporter" for system metrics. So including the visualization tool [Grafana](https://grafana.com/) which is often used to create dashboards the setup looks like this:

<div class="mermaid">
graph LR;
Graphana -- read data --> Prometheus
app1(Exporter / App 1)
app2(Exporter / App 2)
app3(Exporter / App 3)
Prometheus -- pull metrics --> app1 & app2 & app3
</div>

The exporters simply expose the metrics as an HTTP endpoint, say `https://example-api.test/metrics`. The content of the page looks for example like this: 
```
http_requests_total{method="get",code="400"}  3   1395076383000
http_requests_total{method="get",code="200"}  1555   1395076383000
http_requests_total{method="get",code="500"}  0   1395076383000
...
```
In this example one would see how many requests were served up to the time demarked by the timestamp `1395076383000`. These were 1555 HTTP Get requests answered with status code 200, three answered with 400 and none which resulted into a server error with code 500.

This is how Prometheus could be configured to scrape from such an endpoint:
```yaml
global:
  scrape_interval: 15s
  scrape_timeout: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s

scrape_configs:
- job_name: example-api
  honor_labels: true
  honor_timestamps: true
  metrics_path: /metrics
  scheme: https
  static_configs:
  - targets:
    - example-api.test
    labels:
      env: prod
      location: us
```

## Monitoring a Kubernetes deployment
For an application hosted as a "deployment" object on Kubernetes the same approach still works. We can expose the metrics as HTTP endpoint and let Prometheus scrape it. However, one needs to take care to *point Prometheus to the endpoint in every Kubernetes pod and not to access it via an ingress route* and service object, i.e. not via the outward facing url as in the first example above. This is because it might be that multiple replicas of the pod exist. Even if that's not the case in normal operation there might e.g. be an old and a new version during a rolling update. Every pod then only serve some of the requests and with every scraping action Prometheus would get routed to a different pod. Everytime it would see the metrics of another one of the replicas and the numbers would be inconsitent and unusable.

To avoid this problem, Prometheus provides service discovery functionality for Kubernetes, the [kubernetes_sd_config module](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#kubernetes_sd_config). This module accesses the Kubernetes API to discover the pod objects and their IP addresses. Because these IP addresses are only reachable inside the Kubernetes cluster, Prometheus also needs to be run inside the cluster for this. With service discovery we get a setup as follows:
<div class="mermaid">
graph LR;
Prometheus
Prometheus -- discover Pods --> k8s(Kubernetes API)
app1(Exporter <br/> Pod 1)
app2(Exporter <br/> Pod 2)
Prometheus -- pull metrics --> app1 & app2
</div>

The following listing shows a configuration for Prometheus which scrapes the `/metrics` endpoint of all pods with a certain label (`application=example-api`) in the namespace `example-api-prod` in the same cluster. The name of the pod is added as additional label. Here I excluded network port 9443 from scraping, because the same metrics endpoint was also provided under a different port. Prometheus creates one scraping target per pod and exposed network port, so values would be duplicated.
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s

scrape_configs:
  - job_name: 'example-api-pods'

    kubernetes_sd_configs:
    - role: pod
      namespaces:
        names:
        - example-api-prod
      selectors:
        - label: "application=example-api"
          role: pod

    metrics_path: /metrics

    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_container_port_number]
      regex: '9443'
      action: drop
    - action: labelmap
      regex: __meta_kubernetes_pod_label_(.+)
    - source_labels: [__meta_kubernetes_namespace]
      action: replace
      target_label: kubernetes_namespace
    - source_labels: [__meta_kubernetes_pod_name]
      action: replace
      target_label: kubernetes_pod_name
```

In order to get this up and running we need to deploy Prometheus also on Kubernetes. We can deploy it as a StatefulSet:
```yaml
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  labels:
    cluster: us
    environment: prod
  name: prometheus
  namespace: example-api-prod
spec:
  replicas: 1
  selector:
    matchLabels:
      cluster: us
      environment: prod
      module: monitoring
  template:
    metadata:
      labels:
        app: prometheus
        cluster: us
        environment: prod
        module: monitoring
    spec:
      containers:
      - image: prom/prometheus:v2.24.0
        initialDelaySeconds: 15
        livenessProbe:
          httpGet:
            path: /-/healthy
            port: 9090
        name: prometheus
        periodSeconds: 20
        ports:
        - containerPort: 9090
          name: default
        readinessProbe:
          httpGet:
            path: /-/ready
            port: 9090
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          limits:
            cpu: 100m
            memory: 200Mi
          requests:
            cpu: 10m
            memory: 50Mi
        volumeMounts:
        - mountPath: /etc/prometheus/
          name: config-volume
        - mountPath: /prometheus
          name: prometheus-volume
      serviceAccount: prometheus
      serviceAccountName: prometheus
      volumes:
      - configMap:
          name: prometheus-config
        name: config-volume
      - emptyDir: {}
        name: prometheus-volume
```

After deploying this and creating a port forwarding, we can browse the metrics in the Prometheus UI:
```
kubectl apply -f prometheus.yaml
kubectl port-forward prometheus-765d459796-258hz 9090:9090
```

Note that with this configuration the data does not survive a container recreation, because I used an "emptyDir", a temporary directory, as data volume. This only makes sense when this Prometheus instance just serves as a relay for some central instance as described in the next section. But with this setup we could even deploy it as a "Deployment" instead of a "StatefulSet".

## Centralizing monitoring across clusters
Ok, now we have a working Prometheus inside our kubernetes cluster which collects all the metrics of the locally running services. But what if we have multiple clusters, for example in separate regions? Or if we have a central Prometheus instance outside of the cluster and want to relay our data to it?

Nothing easier than that. Because for this we can use one of the central concepts of the Prometheus monitoring landscape: [federation](https://prometheus.io/docs/prometheus/latest/federation/). Prometheus provides this mechanism to create a hierarchy of Prometheus instances where the single instances only scrape a couple of targets and provide the already consolidated metrics for another round of scraping by another Prometheus server. This is how it looks like:

<div class="mermaid">
graph LR;
Graphana -- read data --> central(Central Prometheus)
app1(Exporter / App 1)
app2(Exporter / App 2)
app3(Exporter / App 3)
remote1(Prometheus Spoke 1) -- pull metrics --> app1 & app2
remote2(Prometheus Spoke 2) -- pull metrics --> app3
central -- pull metrics --> remote1 & remote2
</div>

In order to get this concept practically working we can add a service and an ingress route in our kubernetes setup which exposes the built-in `/federate` endpoint. This endpoint provides access to all the metrics.

```yaml
apiVersion: v1
kind: Service
metadata:
  labels:
    app: prometheus
    cluster: us
    environment: prod
    module: monitoring
  name: prometheus-svc
  namespace: example-api-prod
spec:
  ports:
  - port: 80
    protocol: TCP
    targetPort: 9090
  selector:
    app: prometheus
    cluster: us
    environment: prod
    module: monitoring
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: prometheus-ingress
  namespace: example-api-prod
  labels:
    app: prometheus
    cluster: us
    environment: prod
    module: monitoring
spec:
  rules:
  - host: "monitoring.example-api.test"
    http:
      paths:
      - path: /federate
        pathType: Prefix
        backend:
          service:
            name: prometheus-svc
            port:
              number: 80
```
*Note: You will want to add TLS encryption and probably also authentication, so that the federate endpoint and the metrics are not exposed to the internet. In kubernetes this job can be taken by the ingress controller. I'm leaving this out here, because there are different implementations of Ingress controllers whith differing configuration syntax and this is not the focus of this blog post. See for example the [documentation of the nginx ingress controller](https://kubernetes.github.io/ingress-nginx/examples/auth/client-certs/).*

Now we can configure an external Prometheus instance to scrape the metrics from the federated instance. The configuration for Prometheus looks as if it was a normal metrics endpoint. Only we add a `match[]` argument which selects the scraping targets which should be pulled from the federated Prometheus instance:
```yaml
global:
  scrape_interval: 15s
  scrape_timeout: 15s
  evaluation_interval: 15s
scrape_configs:
- job_name: example-api-federate
  honor_labels: true
  honor_timestamps: true
  params:
    match[]:
    - '{job!=""}'
  scrape_interval: 15s
  scrape_timeout: 15s
  metrics_path: /federate
  scheme: http
  static_configs:
  - targets:
    - monitoring.example-api.test
      labels:
        env: prod
        location: us
```
Also here authentication and encryption are missing. A good choice could be TLS client certificates. In the newer Prometheus versions support for this is built in. This is the documentation for the [configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#tls_config) needed on the central server.

Now the central Prometheus server and possibly the Grafana dashboards have access to the metrics of the applications inside the kubernetes cluster!


## Summary

With the setup described above it is possible to monitor applications running in remote kubernetes clusters with a central Prometheus instance. The official documentation about this is a bit scarce, why it took us a while to find this approach. But with the steps explained here it is very simple to set up this monitoring system in a reliable manner. I hope this helps and you spread the word.
