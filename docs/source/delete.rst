=============
Delete Images
=============

Deletes Images from OpenStack(glance).

::

  usage: testbedimage delete_images [-h] [-I IMAGES]

  options:
    -h, --help            show this help message and exit
    -I IMAGES, --images IMAGES
                          imagenames seperated by comma

Command-Line Options
====================

.. confval:: -I IMAGES, --images IMAGES

   A comma-seperated list of image-names to check.

   :default: ``atb-videoserver-image,atb-adminpc-image,atb-attacker-image,atb-corpdns-image,atb-fw-inet-lan-dmz-image``
