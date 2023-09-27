from pydantic import BaseModel
from typing import List


class ImageMeta(BaseModel):
    name: str
    sha256sum: str
    md5sum: str = ""
    disk_format: str
    container_format: str = 'bare'
    size: int = 0


class Manifest(BaseModel):
    date: str
    images: List[ImageMeta] = []
