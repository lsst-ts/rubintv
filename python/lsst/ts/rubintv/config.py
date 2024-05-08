"""Configuration definition."""

import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from safir.logging import LogLevel, Profile

__all__ = ["Configuration", "config"]


class Configuration(BaseSettings):
    """Configuration for rubintv."""

    name: str = Field(
        default="rubintv",
        json_schema_extra={
            "title": "Name of application",
            "validation_alias": "SAFIR_NAME",
        },
    )

    path_prefix: str = Field(
        default="/rubintv",
        json_schema_extra={
            "title": "URL prefix for application",
            "validation_alias": "SAFIR_PATH_PREFIX",
        },
    )

    s3_endpoint_url: str | None = Field(default=os.getenv("S3_ENDPOINT_URL"))

    profile: Profile = Field(
        default=Profile.development,
        json_schema_extra={
            "title": "Application logging profile",
            "validation_alias": "SAFIR_PROFILE",
        },
    )

    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        json_schema_extra={
            "title": "Log level of the application's logger",
            "validation_alias": "SAFIR_LOG_LEVEL",
        },
    )

    model_config = SettingsConfigDict(env_prefix="SAFIR_", case_sensitive=False)


config = Configuration()
"""Configuration for rubintv."""


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
