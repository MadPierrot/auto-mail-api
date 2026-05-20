from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    automx2_url: str = "http://localhost:9999"
    automx2_timeout: int = 15
    log_level: str = "DEBUG"
    domain: str = "example.com"

    # Opzionali: se non impostati nel container, vengono derivati da domain
    activesync_url: Optional[str] = None
    autodiscover_v1_url: Optional[str] = None
    ews_url: Optional[str] = None

    @model_validator(mode="after")
    def build_derived_urls(self) -> "Settings":
        if self.activesync_url is None:
            self.activesync_url = (
                f"https://mail.{self.domain}/Microsoft-Server-ActiveSync"
            )
        if self.autodiscover_v1_url is None:
            self.autodiscover_v1_url = (
                f"https://autodiscover.{self.domain}/autodiscover/autodiscover.xml"
            )
        if self.ews_url is None:
            self.ews_url = f"https://mail.{self.domain}/EWS/Exchange.asmx"
        return self


settings = Settings()
