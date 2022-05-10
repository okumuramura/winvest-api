from pydantic import BaseModel, Field


class User(BaseModel):
    login: str = Field(..., min_length=3, max_length=16)
    password: str = Field(..., min_length=6, max_length=20)
