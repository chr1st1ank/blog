"""
https://github.com/apache/flink-statefun/blob/master/statefun-sdk-protos/src/main/protobuf/sdk/request-reply.proto
"""

import requests
import statefun
import statefun.utils
import statefun.wrapper_types
from statefun.request_reply_pb2 import ToFunction, FromFunction, Address

GREET_REQUEST_TYPE = statefun.make_json_type(typename="example/GreetRequest")
invocation = ToFunction.Invocation(
    argument=statefun.utils.to_typed_value(
        GREET_REQUEST_TYPE, {"name": "George", "visits": 3}
    )
)
# state = ToFunction.PersistedValue(
#     state_name="visits",
#     state_value=statefun.utils.to_typed_value(statefun.wrapper_types.IntType, 5),
# )
invocation_batch_request = ToFunction.InvocationBatchRequest(
    target=Address(namespace="example", type="greeter", id="George"),
    invocations=[invocation],
    # state=[state],
)
request_payload = ToFunction(invocation=invocation_batch_request)

response = requests.post(
    "http://localhost:8000/statefun", data=request_payload.SerializeToString()
)
print(response.status_code)
r = FromFunction()
r.ParseFromString(response.content)
print(r)
# Output is a FromFunction protobuf
# May be checked for validity
# Advisable for correctness testing? Depends, but:
# - Two programs running: statefun & test client
# - Setup, debugging, profiling is a bit harder and slower
# - You're bound to the external interface without the oportunity to do any mocking of internal state. Therefore it might be hard to make strict assumptions about the expected output if the inner logic of the function service is more sophisticated.
