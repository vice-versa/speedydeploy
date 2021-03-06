# -*- coding: utf-8 -*-
from __future__ import with_statement
import os
import sys

from fabric import api as fab
from fabric.contrib import files as fab_files
from fabric.contrib.files import exists

from fab_deploy.utils import run_as

from ..base import _, Daemon
from ..deployment import command
from ..utils import upload_template, upload_first

from cron import CronTab


class RabbitMQ(Daemon):

    namespace = 'rabbitmq'

    def __init__(self, daemon_name=None):
        if daemon_name is None:
            daemon_name = 'rabbitmq-server'
        super(RabbitMQ, self).__init__(daemon_name)

    def install_development_libraries(self):
        os = fab.env.os
        os.install_package('rabbitmq-server')

    @command
    def configure(self):
        self.setup_user()

    def setup_user(self):
        fab.sudo(_('rabbitmqctl add_user %(mq_user)s %(mq_pass)s'))
        fab.sudo(_('rabbitmqctl add_vhost %(mq_domain)s'))
        fab.sudo(_('rabbitmqctl set_permissions'
                  ' -p %(mq_domain)s %(mq_user)s'
                  ' ".*" ".*" ".*"'))


class Celery(Daemon):

    broker = None

    namespace = 'celery'

    supervisor = False
    check_running = True

    def __init__(self, daemon_name=None):
        if daemon_name is None:
            daemon_name = _('%(project_name)s_celeryd')
        super(Celery, self).__init__(daemon_name)

    def dirs(self):
        return ['etc/celery']

    @command
    def configure_daemon(self):
        upload_template('celery/celeryd',
                        _("/etc/init.d/%(project_name)s_celeryd"),
                        context=fab.env,
                        use_jinja=True,
                        use_sudo=True,
                        mode=0755,
                       )

    def put_config(self):
        if not self.supervisor:
            self.configure_daemon()

        upload_template('celery/celeryd.conf',
                        _("%(remote_dir)s/etc/celery/"),
                        context=fab.env,
                        use_jinja=True,
                       )

    def install(self):
        self.put_config()

        with fab.settings(warn_only=True):
            self.stop()
        self.start()

    def update(self):
        self.put_config()
        self.restart()

    @command
    def configure(self, install=False):
        celery = fab.env.celery

        if install:
            celery.install()
        else:
            celery.update()

        if not self.supervisor and self.check_running:
            upload_first(['celery/not_running.mail',
                         ],
                         _("%(remote_dir)s/utils/celery_not_running.mail"),
                         fab.env,
                         use_jinja=True)
            upload_first(['celery/check_running.sh',
                         ],
                         _("%(remote_dir)s/utils/celery_check_running.sh"),
                         fab.env,
                         use_jinja=True)

            fab.run(_("chmod +x %(remote_dir)s/utils/celery_check_running.sh"))

            crontab = CronTab()
            crontab.update(_('*/10 * * * * cat %(remote_dir)s/run/celeryd.pid | xargs ps -p ${1} | grep -v TTY >/dev/null || exec %(remote_dir)s/utils/celery_check_running.sh >/dev/null'),
                           marker='check_celery_running')

    def install_development_libraries(self):
        os = fab.env.os
        if self.broker:
            self.broker.install_development_libraries(self)
        #os.install_package('rabbitmq-server')

    @command
    def restart(self):
        return super(Celery, self).restart()

    def supervisor_start(self, pty=False):
        pass

    def supervisor_configure(self):
        upload_first([_('celery/%(domain)s.supervisor.conf'),
                      'celery/supervisor.conf',
                     ],
                     _('%(remote_dir)s/etc/supervisor/celery.conf'),
                     fab.env,
                     use_jinja=True)
