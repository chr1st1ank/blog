import pickle
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import requests
from sklearn.model_selection import train_test_split

data_folder = Path(__file__).parent.parent / "data"
output_folder = Path(__file__).parent / "output"
output_folder.mkdir(exist_ok=True)
data = pd.read_csv(data_folder / "LanguageDetection.csv", sep=",")


responses: List[requests.Response] = []
session = requests.Session()
for sample in data["Text"].sample(100, random_state=42):
    response = session.get(f"http://localhost:8000/predict?string_input={sample}")
    print(response.status_code, response.text)
    responses.append(
        {
            "response_time": response.elapsed.total_seconds()*1000,
            "status_code": response.status_code,
            "text": sample,
        }
    )

print(pd.DataFrame(responses).describe())
