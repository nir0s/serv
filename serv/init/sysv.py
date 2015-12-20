import os
import sys

import sh

from serv.init.base import Base
from serv import constants as const


class SysV(Base):
    def __init__(self, lgr=None, **params):
        super(SysV, self).__init__(lgr=lgr, **params)
        if self.name:
            self.svc_file_dest = os.path.join(
                const.SYSV_SCRIPT_PATH, self.name)
            self.env_file_dest = os.path.join(
                const.SYSV_ENV_PATH, self.name)

    def generate(self, overwrite=False):
        """Generates a service and env vars file for a SysV service.
        """
        if not os.path.isfile(self.cmd):
            self.lgr.error('The executable {0} does not exist.'.format(
                self.cmd))
            sys.exit()

        self.lgr.debug('Generating Service files.')
        svc_file_tmplt = '{0}_{1}.j2'.format(
            self.init_sys, self.init_sys_ver)
        env_file_tmplt = '{0}_{1}.default.j2'.format(
            self.init_sys, self.init_sys_ver)
        self.generate_file_from_template(
            svc_file_tmplt, self.svc_file_dest, self.params, overwrite)
        self.generate_file_from_template(
            env_file_tmplt, self.env_file_dest, self.params, overwrite)

    def set_system_specific_params(self):
        return {
            'sysv_log_path': '/var/log',
        }

    def install(self):
        """Enables the service"""
        os.chmod(self.svc_file_dest, 755)

    def start(self):
        """Starts the service"""
        self.lgr.debug('Starting SysV Service.')
        try:
            sh.service(self.name, 'start')
        except sh.CommandNotFound:
            # TODO: cleanup generated files if not found.
            self.lgr.warning('service command unavailable. Trying to run '
                             'script directly.')
            try:
                service = sh.Command('/etc/init.d/{0}'.format(self.name))
                service.start(_bg=True)
            except sh.CommandNotFound as ex:
                self.lgr.error('Comnand not found: {0}'.format(str(ex)))
                sys.exit()

    def stop(self):
        self.lgr.debug('Stopping SysV Service.')
        try:
            sh.service(self.name, 'stop')
        except sh.CommandNotFound:
            self.lgr.warning('service command unavailable. Trying to run '
                             'script directly.')
            try:
                service = sh.Command('/etc/init.d/{0}'.format(self.name))
                service.stop()
            except sh.CommandNotFound as ex:
                self.lgr.error('Command not found: {0}'.format(str(ex)))
                sys.exit()

    def uninstall(self):
        self.lgr.debug('Removing SysV Service.')
        if os.path.isfile(self.svc_file_dest):
            os.remove(self.svc_file_dest)
        if os.path.isfile(self.env_file_dest):
            os.remove(self.env_file_dest)

    def is_exist(self):
        return True if os.path.isfile(self.svc_file_dest) else False

    def status(self, name=''):
        """WIP!"""
        raise NotImplementedError()

        try:
            sh.service(name, 'status')
        except sh.CommandNotFound:
            self.lgr.warning('service command unavailable. Trying to run '
                             'script directly.')
            try:
                service = sh.Command('/etc/init.d/{0}'.format(self.name))
            except sh.CommandNotFound as ex:
                self.lgr.error('Command not found: {0}'.format(str(ex)))
                sys.exit()
        svc_info = self._parse_service_info(service.status())
        self.services.update({'services': svc_info})
        return self.services

    @staticmethod
    def _parse_service_info(svc):
        # ssh start/running, process 1214
        s = svc.split()
        name = s[0]
        last_action, status = s[1].split('/')
        try:
            pid = s[2].split()[1]
        except:
            pid = ''
        return dict(
            name=name,
            last_action=last_action,
            status=status,
            pid=pid
        )
