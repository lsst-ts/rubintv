"""Configuration definition."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings
from safir.logging import LogLevel, Profile

__all__ = ["Configuration", "config"]


class Configuration(BaseSettings):
    """Configuration for rubintv."""

    name: str = Field(
        "rubintv",
        json_schema_extra={
            "title": "Name of application",
            "validation_alias": "SAFIR_NAME",
        },
    )

    path_prefix: str = Field(
        "/rubintv",
        json_schema_extra={
            "title": "URL prefix for application",
            "validation_alias": "SAFIR_PATH_PREFIX",
        },
    )

    profile: Profile = Field(
        Profile.development,
        json_schema_extra={
            "title": "Application logging profile",
            "validation_alias": "SAFIR_PROFILE",
        },
    )

    log_level: LogLevel = Field(
        LogLevel.INFO,
        json_schema_extra={
            "title": "Log level of the application's logger",
            "validation_alias": "SAFIR_LOG_LEVEL",
        },
    )


config = Configuration()
"""Configuration for rubintv."""
