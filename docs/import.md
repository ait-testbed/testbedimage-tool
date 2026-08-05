# Importing Images

The `import_images` subcommand fetches the manifest from the image-server. After that it extracts the image locations. Finally it starts a web-import for those images at the Openstack.

!!! note

    Even if the testbedimage-tool initiates the web-import, it is important to know that the Openstack will download the images directly from the image-server.

![Import Images](images/Import_Images.png)

## Command-Line Options

```
usage: testbedimage import_images [-h] [-u URL] [-d]

options:
  -h, --help            show this help message and exit
  -u URL, --url URL     url to the images
  -d, --debug
```

`-u URL, --url URL`
: The URI to the image-server.

  Default: `https://aecidimages.ait.ac.at/current`

`-d`
: Enables debug-output.
