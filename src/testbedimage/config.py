from typing import Optional
from pydantic import BaseModel


class SSHConfig(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    passphrase: Optional[str] = None
    server: str
    port: int = 22
    keyfile: Optional[str] = None
    directory: str = ""


class Webconfig(BaseModel):
    url: str = "https://aecidimages.ait.ac.at/current"
    manifest: str = "Manifest.json"
    local_path: str = "./"
