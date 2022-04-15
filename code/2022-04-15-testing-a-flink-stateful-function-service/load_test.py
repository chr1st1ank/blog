"""load_test.py

A simple load test of the stateful function.
"""

import random

import requests
import statefun
import statefun.utils
import statefun.wrapper_types
from locust import HttpUser, between, task
from statefun.request_reply_pb2 import Address, ToFunction

GREET_REQUEST_TYPE = statefun.make_json_type(typename="example/GreetRequest")


class WebsiteUser(HttpUser):
    wait_time = between(0.01, 0.1)

    @task
    def greeter(self):
        invocation = ToFunction.Invocation(
            argument=statefun.utils.to_typed_value(
                GREET_REQUEST_TYPE, {"name": "George", "visits": random.randint(1, 3)}
            )
        )
        invocation_batch_request = ToFunction.InvocationBatchRequest(
            target=Address(namespace="example", type="greeter", id="George"),
            invocations=[invocation],
        )
        request_payload = ToFunction(invocation=invocation_batch_request)
        self.client.post("/statefun", request_payload.SerializeToString())


# Run with:
# locust --users 20 --run-time 30s -H "http://localhost:8000" --only-summary -f load_test.py
