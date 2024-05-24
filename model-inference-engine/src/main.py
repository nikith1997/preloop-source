import importlib
import logging
import os
from typing import Any, Dict

from fastapi import FastAPI, Header, HTTPException
from passlib.context import CryptContext

inference_module = importlib.import_module("src.inference")

predict_function = getattr(inference_module, os.getenv("PREDICT_FUNCTION_NAME", "predict"))

log = logging.getLogger("uvicorn")

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.post(f"/{os.getenv('ML_MODEL_NAME')}/{os.getenv('URL_VERSION')}")
async def predict_inference(request: Dict[str, Any], key_id: str = Header(None), secret: str = Header(None)):
    try:
        prediction = predict_function(**request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"prediction": prediction}
