from .imageserver import ImageServer
from .testbedexception import TestbedException
from .sftpclient import SFTPClient
from .config import SSHConfig, S3Config, Webconfig
from .manifest import Manifest, ImageMeta
from .httpclient import HttpClient
from typing import Optional, Union
import openstack
import logging
import hashlib
import os
from pathlib import Path
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

    def deploy_images(self, sshcfg: Union[SSHConfig, S3Config]):
        if isinstance(sshcfg, S3Config):
            return self._deploy_images_s3(sshcfg)
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

    def _deploy_images_s3(self, config: S3Config):
        from .s3client import S3Client

        self.logger.info("Checking images...")
        images = self.check_images()
        client = S3Client(config)
        mfst = Manifest(date=client.create_directory())
        for image in images:
            imgmeta = self._download_image_s3(image, client)
            mfst.images.append(imgmeta)
            self.logger.info("Updating Manifest...")
            client.upload_manifest(mfst)

    def _download_image_s3(self, image, client) -> ImageMeta:
        response = ImageServer().download(image)
        md5 = hashlib.md5()
        sha256sum = hashlib.sha256()
        try:
            with Progress() as progress:
                task = progress.add_task(f"[cyan]Deploying {image.name}...",
                                         total=image.size)

                def chunks():
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        md5.update(chunk)
                        sha256sum.update(chunk)
                        progress.update(task, advance=len(chunk))
                        yield chunk
                    # Validate before returning EOF to the managed transfer:
                    # a mismatch must prevent PUT/multipart completion.
                    if response.headers["Content-MD5"] != md5.hexdigest():
                        raise Exception(
                            "Checksum mismatch in downloaded content")

                client.upload_stream(image.name + ".img", chunks(), image.size)
        finally:
            response.close()

        return ImageMeta(name=image.name + ".img",
                         sha256sum=sha256sum.hexdigest(),
                         md5sum=md5.hexdigest(),
                         disk_format=image.disk_format,
                         container_format=image.container_format,
                         size=image.size)

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
            ret = imageserver.find_image_by_name(image)
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
            ret = imageserver.find_image_by_name(image)
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

    def import_images(self, webcfg: Union[Webconfig, S3Config],
                      images: Optional[list[str]] = None):
        if isinstance(webcfg, S3Config):
            return self._import_images_s3(webcfg, images)
        self.logger.info("Checking openstack connection...")
        image_list = []
        imageserver = ImageServer()
        imageserver.test_connection()
        mfst = self.get_manifest(webcfg.url + "/" + webcfg.manifest)
        if images is not None:
            mfst.images = self._select_images(mfst, images)
        with Progress() as progress:
            msg = "Starting imageimport..."
            task = progress.add_task(msg, total=len(mfst.images))
            for image in mfst.images:
                self.logger.info(f"Starting to import {image.name}...")
                ret = imageserver.import_image(image, webcfg.url)
                image_list.append(ret)
                progress.update(task, advance=1)
        self.list_images(list(map(lambda i: i.name, image_list)))

    def _select_images(self, manifest: Manifest, names):
        if names is None:
            return manifest.images
        missing = set(names)
        selected = []
        for image in manifest.images:
            aliases = {image.name, Path(image.name).stem}
            if aliases.intersection(names):
                selected.append(image)
                missing.difference_update(aliases)
        if missing:
            raise TestbedException("Images not in manifest: " +
                                   ", ".join(sorted(missing)))
        return selected

    def _import_images_s3(self, config: S3Config, names):
        from .s3client import S3Client

        client = S3Client(config)
        images = self._select_images(client.get_manifest(), names)
        imageserver = ImageServer()
        with Progress() as progress:
            task = progress.add_task("Starting S3 import...",
                                     total=len(images))
            for image in images:
                self.logger.info("Importing %s from S3...", image.name)
                obj = client.get_object(image.name)
                body = obj["Body"]
                try:
                    size = obj["ContentLength"]
                    if size != image.size:
                        raise TestbedException(
                            f"Size mismatch for {image.name}")
                    imageserver.import_image_stream(image, body, size)
                finally:
                    body.close()
                progress.update(task, advance=1)

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
