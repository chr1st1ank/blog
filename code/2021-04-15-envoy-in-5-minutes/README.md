# Supplements for the blog post "Getting Started with an Envoy Sidecar Proxy in 5 Minutes"

Explanations can be found [in the blog post](https://blog.krudewig-online.de/2021/04/18/envoy-in-5-minutes.html).

Spin up with:
```shell
docker-compose up
```

Send an API request:
```shell
> curl -i 'localhost:8080/calculate?input=xalsjkdf'
HTTP/1.1 200 OK
date: Thu, 06 May 2021 08:25:34 GMT
server: envoy
content-length: 96
content-type: application/json
x-envoy-upstream-service-time: 201

{"input":"xalsjkdf","result":"b5bb764b1ad22b3c2b28261accbbd8f68ca17e88b522d0df3fe1754fc51d59ad"}
```
