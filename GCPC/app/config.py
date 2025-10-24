import json, os
from pydantic import BaseModel

class Config(BaseModel):
    video: dict
    gesture: dict
    clutch: dict
    mapping: dict
    telemetry: dict
    models: dict
    hud: dict

def load_config(path="config.json")->dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
