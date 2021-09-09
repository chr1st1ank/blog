# Run with:
# uvicorn fastapi_main:app --workers 1 --limit-concurrency 1 --port 8080

# Test with:
# go run github.com/codesenberg/bombardier -c 4 -d 10s -l 'localhost:8080/calculate?argument=abc'
import asyncio
import concurrent
import hashlib
from timeit import default_timer as timer
from typing import Tuple

from fastapi import FastAPI, Response
import numpy as np

import sklearn.pipeline
import pickle


app = FastAPI()


@app.on_event("startup")
async def on_startup():
    with open("../training/output/classifier.pickle", "rb") as f:
        model : sklearn.pipeline.Pipeline = pickle.load(f)
        app.state.sklearn_model = model


def predict_language_sklearn(string_input: str) -> Tuple[str, float]:
    probas = app.state.sklearn_model.predict_proba(np.array([string_input]))
    top_index = np.argmax(probas)
    label = app.state.sklearn_model.classes_[top_index]
    return label, probas[0][top_index]


@app.get("/predict")
async def get_predict_sklearn(string_input: str):
    language, confidence = predict_language_sklearn(string_input)
    return {"text": string_input, "language": language, "confidence": confidence}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=8000, workers=1)
