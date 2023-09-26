from .imageserver import ImageServer
from .testbedexception import TestbedException
from .sftpclient import SFTPClient
from .config import SSHConfig, Webconfig
from .manifest import Manifest, ImageMeta
from .httpclient import HttpClient
import openstack
import logging
import hashlib
import bz2
from rich.progress import Progress


class TestbedImage(SFTPClient, HttpClient):
    def __init__(self):
        self.logger = logging.getLogger("rich")
        self.image_list: list[str] = ["atb-videoserver-image",
                                      "atb-adminpc-image",
                                      "atb-attacker-image",
                                      "atb-corpdns-image",
                                      "atb-fw-inet-lan-dmz-image"]
        super().__init__()

    def check_images(self) -> list[openstack.image.v2.image.Image]:
        ret: list[openstack.image.v2.image.Image] = []

        imageserver = ImageServer()
        for img_name in self.image_list:
            image = imageserver.find_image_by_name(img_name)
            if image:
                ret.append(image)
            else:
                raise TestbedException(f"Image {img_name} not found!")
        return ret

    def download_image(self,
                       image: openstack.image.v2.image.Image) -> ImageMeta:
        imageserver = ImageServer()
        md5 = hashlib.md5()
        endsum = hashlib.sha256()
        compressor = bz2.BZ2Compressor()
        with self.sftp_filehandle(image.name + ".bz") as sftpfile:
            response = imageserver.download(image)
            self.logger.debug(image)
            size = 0

            with Progress() as progress:
                msg = "[cyan]Deploying {image.name}..."
                task = progress.add_task(msg, total=image.size)
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    md5.update(chunk)
                    compressed_chunk = compressor.compress(chunk)
                    sftpfile.write(compressed_chunk)
                    endsum.update(compressed_chunk)
                    progress.update(task, advance=len(chunk))
                    size += len(compressed_chunk)

            lastchunk = compressor.flush()
            if lastchunk:
                sftpfile.write(lastchunk)
                endsum.update(lastchunk)
                size += len(lastchunk)

            if response.headers["Content-MD5"] != md5.hexdigest():
                raise Exception("Checksum mismatch in downloaded content")

        return ImageMeta(name=image.name + ".bz",
                         sha256sum=endsum.hexdigest(),
                         disk_format=image.disk_format,
                         size=size,
                         compression='bz')

    def deploy_images(self, sshcfg: SSHConfig):
        self.logger.info("Checking images...")
        images = self.check_images()
        self.logger.info("Connecting to SFTP-Server...")
        self.connect(sshcfg)
        self.logger.info("Creating subdirectory on SFTP-Server...")
        timestamp = self.create_directory()
        mfst = Manifest(date=timestamp)
        for image in images:
            imgmeta = self.download_image(image)
            mfst.images.append(imgmeta)
            self.logger.info("Updating Manifest...")
            self.upload_manifest(mfst)
        self.logger.info("Creating current-link on SFTP-Server...")
        self.current_link()

    def http_down_and_upload_images(self, baseurl: str, image: ImageMeta):
        endsum = hashlib.sha256()
        decompressor = bz2.BZ2Decompressor()
        with self.get_webstream(baseurl + "/" + image.name) as stream:
            for chunk in stream.iter_bytes():
                endsum.update(chunk)
                decompressed = decompressor.decompress(chunk)
                print("TODO")
                print(decompressed)
        if endsum.hexdigest() != image.sha256sum:
            msg = f"sha256sum does not match for {image.name}"
            raise TestbedException(msg)

    def get_images(self, webcfg: Webconfig):
        self.logger.info("Checking openstack connection...")
        # imageserver = ImageServer()
        # imageserver.test_connection()
        mfst = self.get_manifest(webcfg.url + "/" + webcfg.manifest)
        for image in mfst.images:
            print(image)
        self.http_down_and_upload_images(webcfg.url, mfst.images[0])
