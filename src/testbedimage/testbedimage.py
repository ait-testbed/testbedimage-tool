from .imageserver import ImageServer
from .testbedexception import TestbedException
from .sftpclient import SFTPClient
from .config import SSHConfig, Webconfig
from .manifest import Manifest, ImageMeta
from .httpclient import HttpClient
from typing import Optional
import openstack
import logging
import hashlib
from rich.progress import Progress
from rich.table import Table
from rich.console import Console


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
        sha256sum = hashlib.sha256()
        with self.sftp_filehandle(image.name + ".img") as sftpfile:
            response = imageserver.download(image)
            self.logger.debug(image)
            size = 0

            with Progress() as progress:
                msg = f"[cyan]Deploying {image.name}..."
                task = progress.add_task(msg, total=image.size)
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    md5.update(chunk)
                    sha256sum.update(chunk)
                    sftpfile.write(chunk)
                    progress.update(task, advance=len(chunk))
                    size += len(chunk)

            if response.headers["Content-MD5"] != md5.hexdigest():
                raise Exception("Checksum mismatch in downloaded content")

        return ImageMeta(name=image.name + ".img",
                         sha256sum=sha256sum.hexdigest(),
                         md5sum=md5.hexdigest(),
                         disk_format=image.disk_format,
                         container_format=image.container_format,
                         size=image.size)

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
        with self.get_webstream(baseurl + "/" + image.name) as stream:
            for chunk in stream.iter_bytes():
                endsum.update(chunk)
                print("TODO")
        if endsum.hexdigest() != image.sha256sum:
            msg = f"sha256sum does not match for {image.name}"
            raise TestbedException(msg)

    def list_images(self, images: Optional[list[str]] = None):
        if not images:
            images = self.image_list
        imageserver = ImageServer()
        table = Table(title="Status of openstack images")
        table.add_column("Name", style="cyan")
        table.add_column("Status", style="red")
        for image in images:
            ret = imageserver.find_image_by_name(image)
            if ret.status == "active":
                table.add_row(ret.name, f"[green]{ret.status}")
            elif ret.status == "importing":
                table.add_row(ret.name, f"[yellow]{ret.status}")
            else:
                table.add_row(ret.name, ret.status)
        console = Console()
        console.print(table)

    def get_images(self, webcfg: Webconfig):
        self.logger.info("Checking openstack connection...")
        imageserver = ImageServer()
        imageserver.test_connection()
        table = Table(title="Status of uploaded images")
        table.add_column("Name", style="magenta")
        table.add_column("Status", style="cyan")
        for image in self.image_list:
            ret = imageserver.find_image_by_name(image)
            table.add_row(ret.name, ret.status)
        console = Console()
        console.print(table)
        # mfst = self.get_manifest(webcfg.url + "/" + webcfg.manifest)
        # for image in mfst.images:
        #     print(image)
        # self.http_down_and_upload_images(webcfg.url, mfst.images[0])

    def import_images(self, webcfg: Webconfig):
        self.logger.info("Checking openstack connection...")
        image_list = []
        imageserver = ImageServer()
        imageserver.test_connection()
        mfst = self.get_manifest(webcfg.url + "/" + webcfg.manifest)
        with Progress() as progress:
            msg = "Starting imageimport..."
            task = progress.add_task(msg, total=len(mfst.images))
            for image in mfst.images:
                self.logger.info(f"Starting to import {image.name}...")
                ret = imageserver.import_image(image, webcfg.url)
                image_list.append(ret)
                progress.update(task, advance=1)
        self.list_images(image_list)
