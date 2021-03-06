# -*- coding: utf-8 -*-
from __future__ import with_statement
import os

from fabric import api as fab
from fabric.contrib.files import uncomment, comment

from ..base import _
from ..utils import render_template, upload_template
from ..deployment import command


class DjangoProject(object):

    namespace = 'django'

    python_path = '../env/bin/python'
    media_path = '../media'
    settings_local = './settings_local.py'
    version = (1, 3)

    HAS_WSGI = property(lambda self: self.version >= (1, 4))

    USE_LOGGING = True
    USE_SENTRY = True
    USE_CELERY = property(lambda self: hasattr(fab.env, 'celery'))
    USE_SPHINXSEARCH = property(lambda self: hasattr(fab.env, 'sphinxsearch'))

    # app depends
    USE_SOUTH = True
    # TODO get info from settings.py
    USE_STATICFILES = False

    def __init__(self, project_path,
                       settings_local=None,
                       python_path=None):
        self.project_path = project_path
        fab.env['django_project_path'] = project_path

        if settings_local is not None:
            self.settings_local = settings_local
        if python_path is not None:
            self.python_path = python_path

        self.settings_local_path = self.project_path + self.settings_local
        path = fab.env['os'].path
        fab.env['django_project_name'] = path.basename(self.project_path.rstrip('/'))
        fab.env['django_python_path'] = project_path
        fab.env['django_settings'] = 'settings'

    def get_version(self):
        return '.'.join(str(part) for part in self.version)

    def install_requirements(self, update=True):
        opts = '-r'
        if update:
            opts = '-U %s' % opts

        with fab.cd(_('%(django_python_path)s')):
            fab.run(_("../env/bin/pip install %s"
                      " requirements.txt" % opts))

    def run(self, command):
        with fab.cd(_('%(django_python_path)s')):
            fab.run('%s manage.py %s' % (self.python_path,
                                         command)
                   )

    def syncdb(self, app=''):
        self.run('syncdb --noinput %s' % app)

    def migrate(self, app=''):
        self.run('migrate %s' % app)

    def init_debug_server(self):
        self.run('init_debug_server')

    def runserver(self, host="0.0.0.0", port=8080):
        self.run('runserver %s:%s' % (host,port))
    
    def createsuperuser(self):
        self.run('createsuperuser')

    # remove this
    def createshop(self):
        self.run('create_shop')

    @command(same_name=True)
    def update_settings_local(self):
        settings_local_path = fab.env.os.path.join(self.project_path,
                                                   'settings_local.py')

        context = fab.env

        names = ['logging']
        if self.USE_SENTRY:
            names.append('sentry')
        if self.USE_SPHINXSEARCH:
            names.append('sphinxsearch')
        if self.USE_CELERY:
            names.append('celery')

        for name in names:
            if getattr(self, 'USE_' + name.upper(), False):
                text = render_template('django/settings_%s.py' % name,
                                       context=context,
                                       use_jinja=True)
                context['settings_%s' % name] = text
            else:
                context['settings_%s' % name] = ''
       
        upload_template(self.settings_local,
                        settings_local_path,
                        context, use_jinja=True)

    def update_code(self):
        with fab.cd(self.project_path):
            fab.run('svn up')

    def reload(self):
        self.update_settings_local()
        self.syncdb()

        if self.USE_SOUTH:
            self.migrate()
        if self.USE_STATICFILES:
            self.deploy_static()

    def set_maintanance_mode(self, on=True):
        settings_local_path = self.project_path + 'settings_local.py'

        if on:
            uncomment(settings_local_path, r'MAINTENANCE_MODE.*')
        else:
            comment(settings_local_path, r'MAINTENANCE_MODE.*')

    @command
    def deploy_static(self):
        self.run('collectstatic -v0 --noinput')

class Django14(DjangoProject):
    version = (1, 4)

    def __init__(self, *args, **kwargs):
        super(Django14, self).__init__(*args, **kwargs)

        path = fab.env['os'].path
        python_path = path.split(self.project_path.rstrip('/'))[0]
        fab.env['django_python_path'] = python_path
        fab.env['django_settings'] = '%s.settings' % fab.env['django_project_name']
