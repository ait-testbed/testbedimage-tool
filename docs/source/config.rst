=======================
OpenStack Configuration
=======================

In order to use testbedimage it is required to load
the openstack-api configuration. This can be done by
sourcing the openstack openrc-file of the specific
openstack-project:

::

  $ . demo-openrc.sh

.. seealso::
   For more information see the OpenStack documentation:
   https://docs.openstack.org/newton/user-guide/common/cli-set-environment-variables-using-openstack-rc.html

=================
SSL Configuration
=================

To set the path to the ca-certificates use the following environment variable:

::

  $ export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
