from __future__ import annotations

import re
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator


class SiteCreate(BaseModel):
    site_name: str = Field(min_length=2, max_length=100)
    website_url: str = Field(min_length=8, max_length=2048)
    crawl_mode: Literal["standard", "full"] = "standard"
    max_pages: int = Field(default=100, ge=1, le=100_000)
    max_depth: int = Field(default=3, ge=0, le=20)
    include_html: bool = True
    include_pdf: bool = True
    include_txt: bool = True
    include_docx: bool = False
    enable_ocr: bool = True
    languages: list[str] = Field(default_factory=lambda: ["en"])
    excluded_paths: list[str] = Field(default_factory=list)
    respect_robots_txt: bool = True
    logo_url: str | None = None
    accent_color: str = "#0f766e"
    assistant_name: str = "SiteMind Assistant"

    @field_validator("site_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = re.sub(r"\s+", " ", value).strip()
        if not value:
            raise ValueError("Website name cannot be empty.")
        return value

    @field_validator("website_url")
    @classmethod
    def clean_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlparse(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Website URL must be a public HTTP or HTTPS URL.")
        return value

    @field_validator("logo_url")
    @classmethod
    def clean_logo_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        parsed = urlparse(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Logo URL must be a public HTTP or HTTPS URL.")
        return value

    @field_validator("languages")
    @classmethod
    def clean_languages(cls, values: list[str]) -> list[str]:
        clean = []
        for value in values:
            code = re.sub(r"[^a-z-]", "", value.strip().lower())
            if code and code not in clean:
                clean.append(code)
        return clean or ["en"]

    @field_validator("accent_color")
    @classmethod
    def clean_color(cls, value: str) -> str:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value.strip()):
            raise ValueError("Accent color must be a six-digit hexadecimal color.")
        return value.lower()

    @model_validator(mode="after")
    def require_content_type(self) -> "SiteCreate":
        if not any((self.include_html, self.include_pdf, self.include_txt, self.include_docx)):
            raise ValueError("At least one content type must be enabled.")
        return self


class SiteConfig(SiteCreate):
    site_id: str
    allowed_domains: list[str]
    created_at: str
    updated_at: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="default", min_length=1, max_length=100)

    @field_validator("question")
    @classmethod
    def clean_question(cls, value: str) -> str:
        value = re.sub(r"\s+", " ", value).strip()
        if not value:
            raise ValueError("Question cannot be empty.")
        return value


class DeleteSiteRequest(BaseModel):
    confirm_site_id: str


class ConversationReset(BaseModel):
    session_id: str = Field(default="default", min_length=1, max_length=100)


class SiteUpdate(BaseModel):
    assistant_name: str = Field(min_length=2, max_length=100)
    logo_url: str | None = None
    accent_color: str = "#0f766e"
    languages: list[str] = Field(default_factory=lambda: ["en"])

    @field_validator("assistant_name")
    @classmethod
    def clean_assistant_name(cls, value: str) -> str:
        value = re.sub(r"\s+", " ", value).strip()
        if not value:
            raise ValueError("Assistant name cannot be empty.")
        return value

    @field_validator("logo_url")
    @classmethod
    def clean_update_logo_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        parsed = urlparse(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Logo URL must be a public HTTP or HTTPS URL.")
        return value

    @field_validator("accent_color")
    @classmethod
    def clean_update_color(cls, value: str) -> str:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value.strip()):
            raise ValueError("Accent color must be a six-digit hexadecimal color.")
        return value.lower()

    @field_validator("languages")
    @classmethod
    def clean_update_languages(cls, values: list[str]) -> list[str]:
        clean = []
        for value in values:
            code = re.sub(r"[^a-z-]", "", value.strip().lower())
            if code and code not in clean:
                clean.append(code)
        return clean or ["en"]
