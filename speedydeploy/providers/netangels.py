from fabric import api as fab

from ..base import Debian
from ..deployment import _
from ..project import CronTab

from .base import Provider


class NetangelsShared(Provider):

    shared = True

    def __init__(self):
        super(NetangelsShared, self).__init__()

        fab.env.os = Debian()

        fab.env.remote_dir = _("/home/%(user)s/%(instance_name)s/")

        fab.env.cron = CronTab()


class Lite(NetangelsShared):
    pass


class NetangelsVDS(Provider):
    pass


class VDS512(NetangelsVDS):
    pass
