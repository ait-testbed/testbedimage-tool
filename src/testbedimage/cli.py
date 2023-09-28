from argparse import ArgumentParser
import logging
from .testbedimage import TestbedImage
from .config import SSHConfig, Webconfig


DEFAULT_IMAGE_LIST = ("atb-videoserver-image,"
                      "atb-adminpc-image,"
                      "atb-attacker-image,"
                      "atb-corpdns-image,"
                      "atb-fw-inet-lan-dmz-image")


cli = ArgumentParser()
subparsers = cli.add_subparsers(dest="subcommand")


def argument(*name_or_flags, **kwargs):
    """Convenience function to properly format arguments to pass to the
    subcommand decorator.
    """
    return (list(name_or_flags), kwargs)


def subcommand(args=[], parent=subparsers):
    """Decorator to define a new subcommand in a sanity-preserving way.
    The function will be stored in the ``func`` variable when the parser
    parses arguments so that it can be called directly like so::
        args = cli.parse_args()
        args.func(args)
    Usage example::
        @subcommand([argument("-d", help="Enable debug mode",
                     action="store_true")])
        def subcommand(args):
            print(args)
    Then on the command line::
        $ python cli.py subcommand -d
    """
    def decorator(func):
        parser = parent.add_parser(func.__name__, description=func.__doc__)
        for arg in args:
            parser.add_argument(*arg[0], **arg[1])
        parser.set_defaults(func=func)
    return decorator


# @subcommand()
# def nothing(args):
#     print("Nothing special!")


@subcommand([argument("-I", "--images", help="imagenames seperated by comma",
                      default=DEFAULT_IMAGE_LIST),
             argument("-s", "--ssh-server"),
             argument("-P", "--ssh-port", type=int, default=22),
             argument("-u", "--ssh-user"),
             argument("-p", "--ssh-pass"),
             argument("-k", "--ssh-passphrase"),
             argument("-t", "--ssh-directory", default=""),
             argument("-i", "--ssh-keyfile"),
             argument("-d", "--debug", action='store_true')])
def deploy(args):
    logger = logging.getLogger("rich")
    if args.debug:
        logger.setLevel(logging.DEBUG)

    sshconfig = SSHConfig(server=args.ssh_server,
                          port=args.ssh_port,
                          username=args.ssh_user,
                          password=args.ssh_port,
                          directory=args.ssh_directory,
                          keyfile=args.ssh_keyfile)
    tbi = TestbedImage()
    tbi.image_list = args.images.split(",")
    try:
        tbi.deploy_images(sshconfig)
    except Exception as e:
        logger.critical(e)


@subcommand([argument("-u", "--url", help="Url to the images",
                      default="https://aecidimages.ait.ac.at/current"),
             argument("-d", "--debug", action='store_true')])
def get(args):
    logger = logging.getLogger("rich")
    if args.debug:
        logger.setLevel(logging.DEBUG)

    webcfg = Webconfig(url=args.url)
    tbi = TestbedImage()
    try:
        tbi.get_images(webcfg)
    except Exception as e:
        logger.critical(e)


@subcommand([argument("-I", "--images", help="imagenames seperated by comma",
                      default=DEFAULT_IMAGE_LIST),
             argument("-u", "--url", help="url to the images",
                      default="https://aecidimages.ait.ac.at/current"),
             argument("-d", "--debug", action='store_true')])
def import_images(args):
    logger = logging.getLogger("rich")
    if args.debug:
        logger.setLevel(logging.DEBUG)

    webcfg = Webconfig(url=args.url)
    tbi = TestbedImage()
    tbi.image_list = args.images.split(",")
    try:
        tbi.import_images(webcfg)
    except Exception as e:
        logger.critical(e)


@subcommand([argument("-I", "--images", help="imagenames seperated by comma",
                      default=DEFAULT_IMAGE_LIST)])
def list_images(args):
    logger = logging.getLogger("rich")
    tbi = TestbedImage()
    tbi.image_list = args.images.split(",")
    try:
        tbi.list_images()
    except Exception as e:
        logger.critical(e)


@subcommand([argument("-I", "--images", help="imagenames seperated by comma",
                      default=DEFAULT_IMAGE_LIST)])
def delete_images(args):
    logger = logging.getLogger("rich")
    tbi = TestbedImage()
    tbi.image_list = args.images.split(",")
    try:
        tbi.delete_images()
    except Exception as e:
        logger.critical(e)


@subcommand([argument("-u", "--url", help="url to the images",
                      default="https://aecidimages.ait.ac.at/current")])
def manifest(args):
    logger = logging.getLogger("rich")
    tbi = TestbedImage()
    webcfg = Webconfig(url=args.url)
    try:
        tbi.manifest(webcfg)
    except Exception as e:
        logger.critical(e)
