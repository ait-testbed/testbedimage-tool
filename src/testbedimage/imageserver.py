import openstack
from dateutil import parser
from .manifest import ImageMeta
from pathlib import Path


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
