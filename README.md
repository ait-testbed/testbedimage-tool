# testbedimage-tool

This tool helps to import data from the image-repository into the openstack imageservice.
It can also deploy images from the openstack imageserver to a image-repository(sftp)

# Install

```
pip3 install .
```

# Usage

Import all current OpenStack-images to your OpenStack-project:

```
$ export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
$ . myproject-openrc.sh
$ testbedimage import_images
```

# Documentation

* [Documentation](https://aeciddocs.ait.ac.at/testbedimage/current/index.html)
* [Installation](https://aeciddocs.ait.ac.at/testbedimage/current/installation.html)

# License

[GPL-3.0](LICENSE)
