from pydantic import parse_obj_as
import httpx
import json
import logging
from .manifest import Manifest
from .testbedexception import TestbedException


class HttpClient():
    def __init__(self):
        self.logger = logging.getLogger("rich")

    def get_manifest(self, url: str) -> Manifest:
        r = httpx.get(url, follow_redirects=True)
        self.logger.debug(r.headers)

        if r.status_code != 200:
            msg = f"HTTP-Status-Code is not 200: {r.status_code}"
            raise TestbedException(msg)

        mfst_dict = json.loads(r.text)
        return parse_obj_as(Manifest, mfst_dict)

    def get_webstream(self, url: str):
        return httpx.stream("GET", url)
