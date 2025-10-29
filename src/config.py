from pathlib import Path
from typing import Literal

import yaml
from dotenv import find_dotenv, load_dotenv
from loguru import logger
from pydantic import BaseModel, SecretStr
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove


class NodeCode(BaseModel, extra="forbid"):
    name: str
    code: str | None
    content: str
    type: Literal["text", "photo", "voice"]
    message: str


class ConfigYaml(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    tg_token: str
    tg_admin_chat: int

    minio_host: str
    minio_secure: bool
    minio_bucket: str
    minio_access_key: str
    minio_secret_key: SecretStr

    name: str

    start_message: str
    default_message: str
    error_message: str

    back_button: str
    back_message: str

    help_button: str
    help_message: str

    node_codes: list[NodeCode]

    personal: dict[str, str]

    def get_node_codes_reply_markup(self) -> ReplyKeyboardMarkup | ReplyKeyboardRemove:
        keyboard_keys = [node_code.name for node_code in self.node_codes] + [self.help_button]
        keyboard_keys_len = len(self.node_codes)
        if keyboard_keys_len == 0:
            return ReplyKeyboardRemove()
        return ReplyKeyboardMarkup(
            [keyboard_keys[idx : idx + 2] for idx in range(0, keyboard_keys_len, 2)]
            if keyboard_keys_len > 2
            else [[key] for key in keyboard_keys]
        )

    def get_node_by_key(self, key: str) -> NodeCode | None:
        return {node_code.name: node_code for node_code in self.node_codes}.get(key)


def create_config() -> ConfigYaml:
    """
    Создание конфига из файла и переменных окружения
    """

    load_dotenv(find_dotenv())

    configs = Path.cwd() / "config"

    with Path.open(configs / "config.yaml") as stream:
        full_config = yaml.safe_load(stream)

    if not full_config:
        full_config = {}

    config_obj = ConfigYaml(**full_config)

    logger.debug(f"\n{config_obj.model_dump_json(indent=4)}")

    return config_obj


settings = create_config()
