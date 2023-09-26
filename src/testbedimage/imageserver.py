import openstack
from dateutil import parser


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
