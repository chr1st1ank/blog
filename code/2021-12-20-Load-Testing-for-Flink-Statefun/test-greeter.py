"""test-greeter.py

Minimal example of sending a single request to a stateful function.
"""
import json
import pytest
import requests
import statefun
import statefun.utils
import statefun.wrapper_types
from statefun.request_reply_pb2 import Address, FromFunction, ToFunction


@pytest.mark.parametrize(
    "visit, expected_message",
    [
        (1, "Welcome George"),
        (3, "Third time is the charm George"),
    ],
)
def test_correct_greeting(visit, expected_message):
    # Prepare the request
    GREET_REQUEST_TYPE = statefun.make_json_type(typename="example/GreetRequest")
    invocation = ToFunction.Invocation(
        argument=statefun.utils.to_typed_value(
            GREET_REQUEST_TYPE, {"name": "George", "visits": visit}
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

    # Check the output
    assert response.status_code == 200
    egress_message = json.loads(
        from_function.invocation_result.outgoing_egresses[0].argument.value
    )
    assert egress_message["topic"] == "greetings"
    assert egress_message["payload"] == expected_message
