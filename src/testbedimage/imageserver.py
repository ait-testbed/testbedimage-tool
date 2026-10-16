import openstack
import hashlib
import logging
from dateutil import parser
from .manifest import ImageMeta
from pathlib import Path
from .testbedexception import TestbedException


class ImageStream:
    """A known-length, non-seekable upload stream with incremental hashes."""

    def __init__(self, body, size):
        self.body = body
        self.size = size
        self.position = 0
        self.sha256 = hashlib.sha256()
        self.md5 = hashlib.md5()

    def __len__(self):
        return self.size

    def tell(self):
        return self.position

    def __iter__(self):
        while True:
            chunk = self.read(1024 * 1024)
            if not chunk:
                return
            yield chunk

    def read(self, size=-1):
        if size < 0:
            raise ValueError("Image uploads require bounded reads")
        chunk = self.body.read(min(size, 1024 * 1024))
        self.position += len(chunk)
        self.sha256.update(chunk)
        self.md5.update(chunk)
        return chunk

    def verify(self, imgmeta: ImageMeta):
        if self.position != self.size or self.body.read(1):
            raise TestbedException(f"Size mismatch for {imgmeta.name}")
        if self.sha256.hexdigest() != imgmeta.sha256sum:
            raise TestbedException(f"SHA-256 mismatch for {imgmeta.name}")
        if imgmeta.md5sum and self.md5.hexdigest() != imgmeta.md5sum:
            raise TestbedException(f"MD5 mismatch for {imgmeta.name}")


class ImageServer:
    def test_connection(self):
        self.conn.image.images()

    def find_image_by_name(self, name: str) -> openstack.image.v2.image.Image:
        newest = None
        for image in self.conn.image.images():
            if name in image.name:
                if newest:
                    date2 = parser.parse(image.updated_at)
                    date1 = parser.parse(newest.updated_at)
                    if date2 > date1:
                        newest = image
                else:
                    newest = image
        return newest

    def __init__(self):
        openstack.enable_logging(debug=False)
        self.connect()

    def connect(self):
        self.conn = openstack.connect()

    def download(self, image: openstack.image.v2.image.Image):
        return self.conn.image.download_image(image, stream=True)

    def import_image(self, imgmeta: ImageMeta, baseurl: str,
                     visibility: str = "private"
                     ) -> openstack.image.v2.image.Image:
        url = baseurl + "/" + imgmeta.name
        img_name = Path(imgmeta.name).stem
        kwargs = dict(name=img_name,
                      disk_format=imgmeta.disk_format,
                      container_format=imgmeta.container_format,
                      visibility=visibility)

        image = self.conn.image.create_image(**kwargs)
        self.conn.image.import_image(image, method="web-download", uri=url)
        return image

    def delete_image(self, img: openstack.image.v2.image.Image):
        self.conn.image.delete_image(img, ignore_missing=True)

    def import_image_stream(self, imgmeta: ImageMeta, body, size):
        stream = ImageStream(body, size)
        # Always create a new record, so failure cleanup cannot delete an
        # existing image with the same name.
        image = self.conn.image.create_image(
            name=Path(imgmeta.name).stem, disk_format=imgmeta.disk_format,
            container_format=imgmeta.container_format, visibility="private",
            allow_duplicates=True)
        try:
            image.data = stream
            response = image.upload(self.conn.image)
            openstack.exceptions.raise_from_response(response)
            stream.verify(imgmeta)
            active = self.conn.image.wait_for_status(
                image, status="active",
                failures=["killed", "deleted", "error"], wait=3600)
            if active.size is not None and active.size != size:
                raise TestbedException(
                    f"Glance size mismatch for {imgmeta.name}")
            if active.checksum and active.checksum != stream.md5.hexdigest():
                raise TestbedException(
                    f"Glance checksum mismatch for {imgmeta.name}")
            return active
        except Exception:
            try:
                self.delete_image(image)
            except Exception:
                logging.getLogger("rich").exception(
                    "Could not delete failed image %s", image.id)
            raise

    def upload_image(self, imgpath: str,
                     imgmeta: ImageMeta, visibility: str = "private"):
        data = None

        with open(imgpath, "rb") as file:
            data = file.read()

        image_attrs = {'name': imgmeta.name,
                       'data': data,
                       'disk_format': imgmeta.disk_format,
                       'container_format': imgmeta.container_format,
                       'visibility': visibility}
        self.conn.image.upload_image(**image_attrs)
