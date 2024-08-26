import os
import json
from typing import List, Optional, get_origin

from pydantic import BaseModel, root_validator


class JsonModel(BaseModel):
    @root_validator(pre=True)
    def set_default(cls, values):
        """Make not defined values by default types"""
        for key, field in cls.__fields__.items():
            if key not in values:
                if field.default is not None:
                    values[key] = field.default
                else:
                    origin = get_origin(field.outer_type_)
                    if origin is not None:
                        default_type = origin
                    else:
                        default_type = field.outer_type_
                    values[key] = default_type()
        return values


class Database(JsonModel):
    database: str
    user: str
    password: str


class Qiwi(JsonModel):
    token: str
    proxy_url: Optional[str]
    wallet: Optional[str]
    public_key: str


class FakeRequisites(JsonModel):
    russian: List[str]
    ukrainian: List[str]


class Config(JsonModel):
    db: Database

    api_token: str
    admins_id: List[int]
    admins_chat: int

    api_key: str

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
