from pydantic import BaseModel
from typing import List, Dict
import json
import os


class DatabaseConfig(BaseModel):
    database: str
    user: str
    password: str
    host: str = "localhost"


class Config(BaseModel):
    db: DatabaseConfig
    api_token: str
    base_url: str
    default_key: str
    api_key: List[str]
    admins_id: List[int]
    admins_chat: int
    support: str
    time_zone: str = "Europe/Moscow"
    skip_updates: bool = True
    notify: bool = True


def load_config() -> Config:
    if os.path.exists("./settings.json"):
        with open("./settings.json", "r") as f:
            return Config(**json.load(f))
    else:
        with open("./settings.json", "w") as f:
            cfg = Config()
            json.dump(cfg.dict(), f, indent=4)
            print("Blank config created!")
            exit(1)


def save_config(config: Config):
    with open("./settings.json", "w") as f:
        json.dump(config.dict(), f, indent=4)
