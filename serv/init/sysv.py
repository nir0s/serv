import os
import sys
import shutil

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
        super(SysV, self).generate(overwrite=overwrite)
        self._set_system_specific_params()

        self.lgr.debug('Generating Service files.')
        svc_file_tmplt = '{0}_{1}.j2'.format(
            self.init_sys, self.init_sys_ver)
        env_file_tmplt = '{0}_{1}.default.j2'.format(
            self.init_sys, self.init_sys_ver)

        self.svc_file_path = os.path.join(self.tmp, self.name)
        self.env_file_path = os.path.join(self.tmp, self.name + '.defaults')

        files = [self.svc_file_path, self.env_file_path]

        self.generate_file_from_template(
            svc_file_tmplt, self.svc_file_path, self.params, overwrite)
        self.generate_file_from_template(
            env_file_tmplt, self.env_file_path, self.params, overwrite)

        return files

    def install(self):
        """Enables the service"""
        super(SysV, self).install()

        self.lgr.debug('Deploying {0} to {1}...'.format(
            self.svc_file_path, self.svc_file_dest))
        self.create_system_directory_for_file(self.svc_file_dest)
        shutil.move(self.svc_file_path, self.svc_file_dest)
        self.lgr.debug('Deploying {0} to {1}...'.format(
            self.env_file_path, self.env_file_dest))
        self.create_system_directory_for_file(self.env_file_dest)
        shutil.move(self.env_file_path, self.env_file_dest)

        os.chmod(self.svc_file_dest, 755)

    def start(self):
        """Starts the service"""
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

    # TODO: figure out if to depracate.
    def _set_system_specific_params(self):
        self.params.update({
            'sysv_log_dir': '/var/log',
            'sysv_log_path': '/var/log/{0}'.format(self.name)
        })
        ulimits = []
        p = self.params
        if p.get('limit_coredump'):
            ulimits.append('-d {0}'.format(p['limit_coredump']))
        if p.get('limit_cputime'):
            ulimits.append('-t {0}'.format(p['limit_cputime']))
        if p.get('limit_data'):
            ulimits.append('-d {0}'.format(p['limit_data']))
        if p.get('limit_file_size'):
            ulimits.append('-f {0}'.format(p['limit_file_size']))
        if p.get('limit_locked_memory'):
            ulimits.append('-l {0}'.format(p['limit_locked_memory']))
        if p.get('limit_open_files'):
            ulimits.append('-n {0}'.format(p['limit_open_files']))
        if p.get('limit_user_processes'):
            ulimits.append('-u {0}'.format(p['limit_user_processes']))
        if p.get('limit_physical_memory'):
            ulimits.append('-m {0}'.format(p['limit_physical_memory']))
        if p.get('limit_stack_size'):
            ulimits.append('-s {0}'.format(p['limit_stack_size']))
        if ulimits:
            self.params['ulimits'] = ' '.join(ulimits)
