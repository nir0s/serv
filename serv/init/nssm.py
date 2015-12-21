import os
import sys
import subprocess
import shutil
import pkgutil

from distutils.spawn import find_executable

from serv.init.base import Base
from serv import constants as const


class Nssm(Base):
    def __init__(self, lgr=None, **params):
        super(Nssm, self).__init__(lgr=lgr, **params)
        if self.name:
            self.svc_file_dest = os.path.join(
                const.NSSM_SCRIPT_PATH, self.name)
        # 3. run nssm with relevant params to create a service
        # 4. use nssm get to retrieve status of service

    def generate(self, overwrite=False):
        """Generates a service and env vars file for a systemd service.

        Note that env var names will be capitalized using Jinja.
        Even though a param might be named `key` and have value `value`,
        it will be rendered as `KEY=value`.
        """

        if not os.path.isfile(self.cmd):
            self.lgr.error('The executable {0} does not exist.'.format(
                self.cmd))
            sys.exit()

        self.lgr.debug('Generating Service files.')

        # TODO: these should be standardized across all implementations.
        svc_file_tmplt = '{0}_{1}.service.j2'.format(
            self.init_sys, self.init_sys_ver)
        self.generate_file_from_template(
            svc_file_tmplt, self.svc_file_dest, self.params, overwrite)

    def set_system_specific_params(self):
        self.params.update({
            'startup_policy': 'auto',
            'failure_reset_timeout': 60,
            'failure_restart_delay': 5000
        })

    def install(self):
        """Enables the service"""
        self.lgr.debug('Installing nssm Service.')
        self.nssm = \
            self.params.get('nssm_path') \
            or find_executable('nssm') \
            or self._deploy_nssm()
        subprocess.Popen(self.svc_file_dest)

    def start(self):
        """Starts the service"""
        self.lgr.debug('Starting nssm Service.')
        subprocess.Popen('sc start {0}'.format(self.name))

    def stop(self):
        self.lgr.debug('Stopping nssm Service.')
        subprocess.Popen('sc stop {0}'.format(self.name))

    # TODO: this should be a decorator under base.py to allow
    # cleanup on failed creation.
    def uninstall(self):
        self.lgr.debug('Removing nssm Service.')
        subprocess.Popen('sc config {0} start= disabled'.format(self.name))
        subprocess.Popen('{0} remove {1} confirm'.format(self.nssm, self.name))
        if os.path.isfile(self.svc_file_dest):
            os.remove(self.svc_file_dest)

    def is_exist(self):
        return True if os.path.isfile(self.svc_file_dest) else False

    def status(self, name):
        result = subprocess.Popen('{0} status {1}'.format(
            self.nssm_path, self.name))
        # apparently nssm output is encoded in utf16.
        # encode to ascii to be able to parse this
        state = result.std_out.decode('utf16').encode('utf-8').rstrip()
        self.services.update(
            {'services': [dict(name=self.name, status=state)]})
        return self.services

    def _deploy_nssm(self):
        exec_path = pkgutil.get_data(__name__, os.path.join(
            'binaries', 'nssm.exe'))
        if not os.path.isdir('c:\\nssm'):
            os.makedirs('c:\\nssm')
        shutil.copyfile(exec_path, 'c:\\nssm\\nssm.exe')
