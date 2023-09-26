from pydantic import BaseModel
from typing import List, Literal


class ImageMeta(BaseModel):
    name: str
    sha256sum: str
    compression: Literal['bz']
    disk_format: str
    size: int = 0


class Manifest(BaseModel):
    date: str
    images: List[ImageMeta] = []
