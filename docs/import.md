# Importing Images

The `import_images` subcommand fetches the manifest from the image-server. After that it extracts the image locations. Finally it starts a web-import for those images at the Openstack.

!!! note

    Even if the testbedimage-tool initiates the web-import, it is important to know that the Openstack will download the images directly from the image-server.

![Import Images](images/Import_Images.png)

## Command-Line Options

```
usage: testbedimage import_images [-h] [-u URL] [-I IMAGES]
                                 [--s3-bucket S3_BUCKET]
                                 [--s3-endpoint S3_ENDPOINT]
                                 [--s3-region S3_REGION]
                                 [--s3-prefix S3_PREFIX]
                                 [--s3-profile S3_PROFILE] [-d]

options:
  -h, --help            show this help message and exit
  -u URL, --url URL     url to the images
  -I IMAGES, --images IMAGES
                        image names separated by comma
  -d, --debug
```

`-u URL, --url URL`
: The URI to the image-server.

  Default: `https://aecidimages.ait.ac.at/current`

`-d`
: Enables debug-output.

## Import from S3

Run from the repository root:

```sh
uv run testbedimage import_images \
  --s3-bucket attackbed \
  --s3-endpoint https://s3.eu-west-par.io.cloud.ovh.net \
  --s3-region eu-west-par \
  --s3-prefix 'test/2026-10-15T13:27:48' \
  --s3-profile attackbed-paris
```

Use your actual release prefix, including its timestamp. This streams image
bytes directly into Glance; `--url` retains the existing `web-download` mode.
OpenStack image names omit the `.img` extension.

For either source, add `--images name1,name2` to select manifest entries by
filename, with or without `.img`. Omit it to import all entries.
