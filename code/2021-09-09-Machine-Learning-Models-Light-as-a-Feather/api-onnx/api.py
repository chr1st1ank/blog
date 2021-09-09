from typing import Tuple

from fastapi import FastAPI
import onnxruntime
import numpy as np


app = FastAPI()


@app.on_event("startup")
async def on_startup():
    """Load the model at service startup"""
    # Set some session parameters for better performance
    sess_options = onnxruntime.SessionOptions()
    sess_options.intra_op_num_threads = 1
    sess_options.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
    sess_options.graph_optimization_level = (
        onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
    )
    # Load the model
    app.state.onnx_session = onnxruntime.InferenceSession(
        "../training/output/classifier.onnx", sess_options
    )


def predict_language(string_input: str) -> Tuple[str, float]:
    """Runs a prediction using the onnx model and returns the most likely label and confidence"""
    pred_onx = app.state.onnx_session.run(
        None, {"string_input": np.array([string_input]).reshape(1, 1)}
    )
    label = pred_onx[0][0]
    probas = pred_onx[1][0]
    return label, probas[label]


@app.get("/predict")
async def get_predict(string_input: str):
    """Endpoint definition for the /predict endpoint of the service"""
    language, confidence = predict_language(string_input)
    return {"text": string_input, "language": language, "confidence": confidence}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8000, workers=1)
