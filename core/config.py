from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    server_adress: str = Field(..., alias="SERVER_ADDRESS")
    postgress_conn: str = Field(..., alias="POSTGRES_CONN")


setings = Settings()
