import pkgutil
import os
import json
import sys
from distutils.spawn import find_executable

import jinja2


class Base(object):
    def __init__(self, lgr=None, **params):
        self.lgr = lgr
        self.params = params

        self.init_sys = params.get('init_sys')
        self.init_sys_ver = params.get('init_sys_ver')
        self.cmd = params.get('cmd')
        self.name = params.get('name')

        # only relevant when retrieving status.
        self.services = dict(
            init_system=self.init_sys,
            init_system_version=self.init_sys_ver,
            services=[]
        )

        # only relevant when creating a service
        if self.cmd:
            if not find_executable(self.cmd):
                self.lgr.error('Executable {0} could not be found.'.format(
                    self.cmd))
                sys.exit()

    def generate(self, overwrite):
        """Generates service files.
        """
        raise NotImplementedError('Must be implemented by a subclass')

    def install(self):
        """Installs a service.

        This is relevant for init systems like systemd where you have to
        `sudo systemctl enable #SERVICE#` before starting a service.
        """
        raise NotImplementedError('Must be implemented by a subclass')

    def start(self):
        """Starts a service.
        """
        raise NotImplementedError('Must be implemented by a subclass')

    def stop(self):
        """Stops a service.
        """
        raise NotImplementedError('Must be implemented by a subclass')

    def uninstall(self):
        """Uninstalls a service.

        This should include any cleanups required.
        """
        raise NotImplementedError('Must be implemented by a subclass')

    def status(self, name=''):
        """Retrieves the status of a service `name` or all services
        for the current init system.
        """
        raise NotImplementedError('Must be implemented by a subclass')

    def generate_file_from_template(self, template, destination, params,
                                    overwrite=False):
        """Generates a file from a Jinja2 `template` and writes it to
        `destination` using `params`.

        `overwrite` allows to overwrite existing files.

        This used used by the different init implementations to generate
        init scripts/configs and deploy them to the relevant directories.
        Templates are looked up under init/templates/`template`.

        If the `destination` dir doesn't exist, it will be created.
        While it may seem a bit weird, not all relevant directories exist
        out of the box. For instance, `/etc/sysconfig` doesn't necessarily
        exist even if systemd is used by default.
        """
        templates = pkgutil.get_data(__name__, os.path.join(
            'templates', template))

        pretty_params = json.dumps(params, indent=4, sort_keys=True)
        self.lgr.debug('Rendering {0} with params: {1}...'.format(
            template, pretty_params))
        generated = jinja2.Environment().from_string(templates).render(params)

        dirname = os.path.dirname(destination)
        if not os.path.isdir(dirname):
            self.lgr.debug('Creating destination directory: {0}...'.format(
                dirname))
            os.makedirs(dirname)

        self.lgr.debug('Writing generated file to {0}...'.format(destination))
        if os.path.isfile(destination):
            if overwrite:
                self.lgr.debug('Overwriting: {0}'.format(destination))
            else:
                self.lgr.error('File already exists: {0}'.format(destination))
                sys.exit()
        with open(destination, 'w') as f:
            f.write(generated)
