"""
https://locust.io/
https://github.com/apache/flink-statefun/blob/master/statefun-sdk-protos/src/main/protobuf/sdk/request-reply.proto
"""

import requests
import statefun
import statefun.utils
import statefun.wrapper_types
from statefun.request_reply_pb2 import ToFunction, FromFunction, Address

GREET_REQUEST_TYPE = statefun.make_json_type(typename="example/GreetRequest")

# response = requests.post(
#     "http://localhost:8888/statefun", data=request_payload.SerializeToString()
# )
# print(response.status_code)
# r = FromFunction()
# r.ParseFromString(response.content)
# print(r)


from locust import HttpUser, between, task


class WebsiteUser(HttpUser):
    # wait_time = between(5, 15)

    @task
    def greeter(self):
        invocation = ToFunction.Invocation(
            argument=statefun.utils.to_typed_value(
                GREET_REQUEST_TYPE, {"name": "George", "visits": 3}
            )
        )
        invocation_batch_request = ToFunction.InvocationBatchRequest(
            target=Address(namespace="example", type="greeter", id="George"),
            invocations=[invocation],
        )
        request_payload = ToFunction(invocation=invocation_batch_request)
        self.client.post("/statefun", request_payload.SerializeToString())


# locust --users 5 --run-time 30s -H "http://localhost:8888" --only-summary -f load_test.py
