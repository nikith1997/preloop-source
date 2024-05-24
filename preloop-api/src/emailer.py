import requests

import src.models


def send_email(email: src.models.Email):
    url = "https://1a7735d0k0.execute-api.us-east-1.amazonaws.com/prod/"
    body = email.model_dump()
    body["from"] = body["from_"]
    del body["from_"]

    response = requests.post(url, json=body)
    if response.status_code != 200:
        raise ValueError("Email not sent do to error.")
    return
