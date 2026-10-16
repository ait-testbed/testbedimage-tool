# testbedimage-tool

This tool helps to import data from the image-repository into the openstack imageservice.
It can also deploy images from the openstack imageserver to a image-repository(sftp)

# Install

From the repository root, using [uv](https://docs.astral.sh/uv/getting-started/installation/):

```sh
uv sync
```

# Usage

Import all current OpenStack-images to your OpenStack-project:

```
$ export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
$ . myproject-openrc.sh
$ uv run testbedimage import_images
```

# Documentation

* [Documentation](https://ait-testbed.github.io/testbedimage-tool/)
* [Installation](https://ait-testbed.github.io/testbedimage-tool/latest/installation/)

# License

[GPL-3.0](LICENSE)
