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
        self.args = params.get('args', '')
        self.description = params.get('description', 'no description given')
        self.user = params.get('user', 'root')
        self.group = params.get('group', 'root')
        self.chdir = params.get('chdir', '/')
        self.chroot = params.get('chroot', '/')

        self.services = dict(
            init_system=self.init_sys,
            init_system_version=self.init_sys_ver,
            services=[]
        )

        # only relevant when creating a service
        if self.cmd:
            if not find_executable(self.cmd):
                self.lgr.error('Executable {0} could not be found.')
                sys.exit()

    def generate(self, overwrite):
        raise NotImplementedError('Must be implemented by a subclass')

    def install(self):
        raise NotImplementedError('Must be implemented by a subclass')

    def start(self):
        raise NotImplementedError('Must be implemented by a subclass')

    def stop(self):
        raise NotImplementedError('Must be implemented by a subclass')

    def uninstall(self):
        raise NotImplementedError('Must be implemented by a subclass')

    def status(self, name=''):
        raise NotImplementedError('Must be implemented by a subclass')

    def generate_file_from_template(self, template, destination, params,
                                    overwrite=False):
        templates = pkgutil.get_data(__name__, os.path.join(
            'templates', template))

        pretty_params = json.dumps(params, indent=4, sort_keys=True)
        self.lgr.debug('Rendering {0} with params: {1}...'.format(
            template, pretty_params))
        generated = jinja2.Environment().from_string(templates).render(params)

        dirname = os.path.dirname(destination)
        if not os.path.isdir(dirname):
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
