"""single-request.py

Minimal example of sending a single request to a stateful function.
"""
import requests
import statefun
import statefun.utils
import statefun.wrapper_types
from statefun.request_reply_pb2 import Address, FromFunction, ToFunction

# Prepare the request
GREET_REQUEST_TYPE = statefun.make_json_type(typename="example/GreetRequest")
invocation = ToFunction.Invocation(
    argument=statefun.utils.to_typed_value(
        GREET_REQUEST_TYPE, {"name": "George", "visits": -3}
    )
)
invocation_batch_request = ToFunction.InvocationBatchRequest(
    target=Address(namespace="example", type="greeter", id="George"),
    invocations=[invocation],
)
request_payload = ToFunction(invocation=invocation_batch_request)

# Send the request and receive the response
response = requests.post(
    "http://localhost:8000/statefun", data=request_payload.SerializeToString()
)

# Parse and print the response
from_function = FromFunction()
from_function.ParseFromString(response.content)

print(f"{response.status_code=}")
print(f"{from_function=}")
