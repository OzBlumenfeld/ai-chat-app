"""Example script demonstrating Pydantic settings with remote configuration."""

from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class ExampleSettings(BaseSettings):
    """Example settings class that merges remote configuration."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    MY_INT: int
    MY_FLOAT: float
    MY_LIST: list[str]

    def __init__(self, **values: Any) -> None:
        """Initialize settings with merged remote values."""
        merged_values = values.copy()

        # simulated remote load
        remote = {"MY_INT": "123", "MY_FLOAT": "1.23", "MY_LIST": '["a", "b"]'}
        merged_values.update(remote)

        print(f"merged_values before super: {merged_values}")
        super().__init__(**merged_values)
        print(f"self.MY_INT type: {type(self.MY_INT)}")


if __name__ == "__main__":
    t = ExampleSettings()
    print(t.model_dump())
