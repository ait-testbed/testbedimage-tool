"""S3 deployment and release-reading helpers."""

from datetime import datetime

import boto3
from boto3.s3.transfer import TransferConfig

from .config import S3Config
from .manifest import Manifest


class ChunkReader:
    """Adapt chunks to non-seekable reads, filling each requested read size.

    Managed transfers probe the multipart threshold before choosing PUT.
    Their only unbounded read is for the remainder of a below-threshold
    object, so buffering stays bounded by the threshold/part size.
    """

    def __init__(self, chunks):
        self.chunks = iter(chunks)
        self.pending = b""

    def read(self, size=-1):
        if size == 0:
            return b""
        parts = []
        remaining = size
        while remaining != 0:
            if not self.pending:
                try:
                    self.pending = next(self.chunks)
                except StopIteration:
                    break
                if not self.pending:
                    continue
            count = len(self.pending) if size < 0 else remaining
            part = self.pending[:count]
            self.pending = self.pending[len(part):]
            parts.append(part)
            if size >= 0:
                remaining -= len(part)
        return b"".join(parts)


class S3Client:
    def __init__(self, config: S3Config):
        self.config = config
        session = boto3.Session(profile_name=config.profile)
        self.client = session.client("s3", endpoint_url=config.endpoint_url,
                                     region_name=config.region)

    def create_directory(self) -> str:
        timestamp = datetime.now().isoformat(timespec='seconds')
        self.release_prefix = "/".join(filter(None, (
            self.config.prefix.strip("/"), timestamp)))
        return timestamp

    def upload_stream(self, filename, chunks, size):
        # Allow large images without exceeding S3's 10,000-part limit.
        part_size = max(16 * 1024 * 1024, (size + 9999) // 10000)
        transfer = TransferConfig(multipart_threshold=16 * 1024 * 1024,
                                  multipart_chunksize=part_size,
                                  use_threads=False,
                                  preferred_transfer_client="classic")
        self.client.upload_fileobj(
            ChunkReader(chunks), self.config.bucket,
            self.release_prefix + "/" + filename, Config=transfer)

    def upload_manifest(self, mfst: Manifest):
        self.client.put_object(Bucket=self.config.bucket,
                               Key=self.release_prefix + "/Manifest.json",
                               Body=mfst.json().encode("utf-8"),
                               ContentType="application/json")

    def get_object(self, filename):
        key = "/".join(filter(None, (self.config.prefix.strip("/"), filename)))
        return self.client.get_object(Bucket=self.config.bucket, Key=key)

    def get_manifest(self) -> Manifest:
        body = self.get_object("Manifest.json")["Body"]
        try:
            return Manifest.parse_raw(body.read())
        finally:
            body.close()
