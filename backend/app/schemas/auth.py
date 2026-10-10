from pydantic import BaseModel, Field, SecretStr, field_validator


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_]+$")
    password: SecretStr = Field(min_length=12, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize(cls, value):
        return value.lower()


class User(BaseModel):
    id: str
    username: str


class AuthState(BaseModel):
    enabled: bool
    user: User | None = None
