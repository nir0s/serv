import os
import sys
import subprocess
import shutil

from distutils.spawn import find_executable

from serv.init.base import Base
from serv import constants as const


class Nssm(Base):
    def __init__(self, lgr=None, **params):
        super(Nssm, self).__init__(lgr=lgr, **params)
        raise NotImplementedError('nssm is not ready yet. Come back soon...')
        if self.name:
            self.svc_file_dest = os.path.join(
                const.NSSM_SCRIPT_PATH, self.name)

    def generate(self, overwrite=False):
        """Generates a service and env vars file for a nssm service.

        Note that env var names will be capitalized using Jinja.
        Even though a param might be named `key` and have value `value`,
        it will be rendered as `KEY=value`.
        """
        super(Nssm, self).generate(overwrite=overwrite)
        self._set_system_specific_params()

        self.lgr.debug('Generating Service files.')
        svc_file_tmplt = '{0}_{1}.conf.j2'.format(
            self.init_sys, self.init_sys_ver)

        self.svc_file_path = os.path.join(self.tmp, self.name)

        files = [self.svc_file_path]

        self.generate_file_from_template(svc_file_tmplt, self.svc_file_path)

        return files

    def install(self):
        """Enables the service"""
        super(Nssm, self).install()
        self.deploy_service_file(
            self.svc_file_path, self.svc_file_dest, create_directory=True)

        self.nssm = \
            self.params.get('nssm_path') \
            or find_executable('nssm') \
            or self._deploy_nssm_binary()
        subprocess.Popen(self.svc_file_dest)

    def start(self):
        """Starts the service"""
        subprocess.Popen('sc start {0}'.format(self.name))

    def stop(self):
        subprocess.Popen('sc stop {0}'.format(self.name))

    # TODO: this should be a decorator under base.py to allow
    # cleanup on failed creation.
    def uninstall(self):
        subprocess.Popen('sc config {0} start= disabled'.format(self.name))
        subprocess.Popen('{0} remove {1} confirm'.format(self.nssm, self.name))
        if os.path.isfile(self.svc_file_dest):
            os.remove(self.svc_file_dest)

    def status(self, name):
        result = subprocess.Popen('{0} status {1}'.format(
            self.nssm_path, self.name))
        # apparently nssm output is encoded in utf16.
        # encode to ascii to be able to parse this
        state = result.std_out.decode('utf16').encode('utf-8').rstrip()
        self.services.update(
            {'services': [dict(name=self.name, status=state)]})
        return self.services

    def is_system_exists(self):
        """Returns True always since if it isn't installed, it will be.

        See `self.install`
        """
        return True

    def is_service_exists(self):
        raise NotImplementedError()

    def _deploy_nssm_binary(self):
        # still not sure whether we should use this or
        # is_pyx32 = True if struct.calcsize("P") == 4 else False
        # TODO: check what checks for OS arch and which checks Python arch.
        is_64bits = sys.maxsize > 2 ** 32
        binary = 'nssm64.exe' if is_64bits else 'nssm32.exe'
        source = os.path.join(os.path.dirname(__file__), 'binaries', binary)
        destination = os.path.join(const.NSSM_BINARY_LOCATION, 'nssm.exe')
        if not os.path.isdir(const.NSSM_BINARY_LOCATION):
            os.makedirs(const.NSSM_BINARY_LOCATION)
        self.lgr.debug('Deploying {0} to {1}...'.format(source, destination))
        shutil.copyfile(source, destination)
        return destination

    def _set_system_specific_params(self):
        # should of course be configurable
        self.params.update({
            'startup_policy': 'auto',
            'failure_reset_timeout': 60,
            'failure_restart_delay': 5000
        })
