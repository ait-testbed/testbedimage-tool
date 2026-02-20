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
import os
from rich.progress import Progress
from rich.table import Table
from rich.console import Console
from rich.prompt import Prompt


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

    def http_get_image(self, baseurl: str,
                       local_path: str, image: ImageMeta) -> str:
        endsum = hashlib.sha256()

        local_file = os.path.join(local_path, image.name)
        url = baseurl + "/" + image.name
        self.logger.debug(f"Url: {url}")
        self.logger.debug(f"Local path: {local_file}")

        with self.get_webstream(url) as stream:
            with open(local_path + "/" + image.name, "wb") as imgfile:
                for chunk in stream.iter_bytes():
                    endsum.update(chunk)
                    imgfile.write(chunk)
                imgfile.flush()

        if endsum.hexdigest() != image.sha256sum:
            msg = f"sha256sum does not match for {image.name}"
            raise TestbedException(msg)
        return local_file

    def list_images(self, images: Optional[list[str]] = None):
        if not images:
            images = self.image_list
        imageserver = ImageServer()
        table = Table(title="Status of openstack images")
        table.add_column("Name", style="cyan")
        table.add_column("Status", style="red")
        for image in images:
            ret = imageserver.find_image_by_name(image.name)
            if not ret:
                continue
            if ret.status == "active":
                table.add_row(ret.name, f"[green]{ret.status}")
            elif ret.status == "importing":
                table.add_row(ret.name, f"[yellow]{ret.status}")
            else:
                table.add_row(ret.name, ret.status)
        console = Console()
        console.print(table)

    def delete_images(self, images: Optional[list[str]] = None):
        if not images:
            images = self.image_list
        imageserver = ImageServer()
        for image in images:
            ret = imageserver.find_image_by_name(image.name)
            msg = f"Do you really want to delete {ret.name}?"
            choice = Prompt.ask(msg, choices=["y", "N"], default="N")
            if choice == "y":
                self.logger.info(f"Deleting {ret.name}...")
                imageserver.delete_image(ret)
            else:
                self.logger.info(f"Abort deleting {ret.name}...")

    def get_images(self, webcfg: Webconfig):
        self.logger.info("Checking openstack connection...")
        imageserver = ImageServer()
        imageserver.test_connection()
        mfst = self.get_manifest(webcfg.url + "/" + webcfg.manifest)
        with Progress() as progress:
            msg = "Starting Imagetransfer..."
            task = progress.add_task(msg, total=len(mfst.images) * 2)
            for imgmeta in mfst.images:
                self.logger.info(f"Downloading {imgmeta.name}")
                imgfile = self.http_get_image(webcfg.url,
                                              webcfg.local_path, imgmeta)
                progress.update(task, advance=1)
                self.logger.info(f"Uploading {imgmeta.name} to Openstack")
                imageserver.upload_image(imgfile, imgmeta)
                progress.update(task, advance=1)

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

    def manifest(self, webcfg: Webconfig):
        mfst = self.get_manifest(webcfg.url + "/" + webcfg.manifest)
        console = Console()
        url = webcfg.url + "/" + webcfg.manifest
        console.print(f"Manifest-Url: {url}")
        console.print(f"Date: {mfst.date}")
        for imgmeta in mfst.images:
            table = Table()
            inner = Table(show_header=False)
            inner.add_column(None, style="white")
            inner.add_column()
            table.add_column(imgmeta.name, style="cyan")
            inner.add_row("[bold]sha256sum:", imgmeta.sha256sum)
            inner.add_row("[bold]md5sum:", imgmeta.md5sum)
            inner.add_row("[bold]disk:", imgmeta.disk_format)
            inner.add_row("[bold]container:", imgmeta.container_format)
            inner.add_row("[bold]size:", str(imgmeta.size))
            table.add_row(inner)
            console.print(table)
