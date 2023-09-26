from paramiko.client import SSHClient
from paramiko import AutoAddPolicy

from testbedimage.manifest import Manifest
from .config import SSHConfig
from datetime import datetime
import os.path
import errno


class SFTPClient:
    def __init__(self):
        self.sshcfg = None

    def connect(self, sshcfg: SSHConfig):
        self.sshcfg = sshcfg
        self.client = SSHClient()
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(AutoAddPolicy())

        self.client.connect(hostname=self.sshcfg.server,
                            port=self.sshcfg.port,
                            username=self.sshcfg.username,
                            password=self.sshcfg.password,
                            passphrase=self.sshcfg.passphrase,
                            key_filename=self.sshcfg.keyfile)

    def create_directory(self) -> str:
        self.timestamp = datetime.now().isoformat(timespec='seconds')
        self.serverpath = os.path.join(self.sshcfg.directory, self.timestamp)
        self.client.open_sftp().mkdir(self.serverpath)
        return self.timestamp

    def sftp_filehandle(self, filename: str):
        sftppath = os.path.join(self.serverpath, filename)
        return self.client.open_sftp().file(sftppath, "wb")

    def upload_manifest(self, mfst: Manifest):
        mfst_path = os.path.join(self.serverpath, "Manifest.json")
        with self.client.open_sftp().file(mfst_path, "w") as fo:
            fo.write(mfst.json())

    def current_link(self):
        current_path = os.path.join(self.sshcfg.directory, "current")
        try:
            self.client.open_sftp().unlink(current_path)
        except OSError as e:
            if e.errno == errno.ENOENT:
                pass
        self.client.open_sftp().symlink(self.timestamp, current_path)
