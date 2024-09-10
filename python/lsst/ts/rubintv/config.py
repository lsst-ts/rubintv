"""Configuration definition."""

import os
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from structlog import get_logger

__all__ = ["Configuration", "config", "rubintv_logger"]


def where_am_i() -> str:
    location = os.getenv("RAPID_ANALYSIS_LOCATION", "")
    if location == "BTS":
        return "base"
    if location == "TTS":
        return "tucson"
    if location == "SUMMIT":
        return "summit"
    if location == "USDF":
        return "usdf-k8s"
    if os.getenv("GITHUB_ACTIONS", ""):
        return "gha"
    else:
        return "local"


class Configuration(BaseSettings):
    """Configuration for rubintv."""

    name: str = Field(
        default="rubintv",
        validation_alias="SAFIR_NAME",
        json_schema_extra={"title": "Name of application"},
    )

    path_prefix: str = Field(
        default="/rubintv",
        validation_alias="SAFIR_PATH_PREFIX",
        json_schema_extra={"title": "URL prefix for application"},
    )

    site_location: str = where_am_i()

    s3_endpoint_url: str = Field(default="testing", alias="S3_ENDPOINT_URL")

    model_config = SettingsConfigDict(env_prefix="SAFIR_", case_sensitive=False)


config = Configuration()
"""Configuration for rubintv."""


def rubintv_logger() -> Any:
    logger = get_logger()
    return logger
