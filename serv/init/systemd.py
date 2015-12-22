import os
import sys
import shutil

import sh

from serv.init.base import Base
from serv import constants as const


class SystemD(Base):
    def __init__(self, lgr=None, **params):
        super(SystemD, self).__init__(lgr=lgr, **params)
        if self.name:
            self.svc_file_dest = os.path.join(
                const.SYSTEMD_SVC_PATH, self.name + '.service')
            self.env_file_dest = os.path.join(
                const.SYSTEMD_ENV_PATH, self.name)

    def generate(self, overwrite=False):
        """Generates a service and env vars file for a systemd service.

        Note that env var names will be capitalized using Jinja.
        Even though a param might be named `key` and have value `value`,
        it will be rendered as `KEY=value`.
        """
        super(SystemD, self).generate(overwrite=overwrite)
        self._validate_init_system_params()

        self.lgr.debug('Generating Service files.')

        # TODO: these should be standardized across all implementations.
        svc_file_tmplt = '{0}_{1}.service.j2'.format(
            self.init_sys, self.init_sys_ver)
        env_file_tmplt = '{0}_{1}.env.j2'.format(
            self.init_sys, self.init_sys_ver)

        self.svc_file_path = os.path.join(self.tmp, self.name + '.service')
        self.env_file_path = os.path.join(self.tmp, self.name)

        files = [self.svc_file_path]

        self.generate_file_from_template(
            svc_file_tmplt, self.svc_file_path, self.params, overwrite)
        if self.params.get('env'):
            self.generate_file_from_template(
                env_file_tmplt, self.env_file_path, self.params, overwrite)
            files.append(self.env_file_path)

        return files

    def install(self):
        """Enables the service"""
        super(SystemD, self).install()

        self.lgr.debug('Deploying {0} to {1}...'.format(
            self.svc_file_path, self.svc_file_dest))
        self.create_system_directory_for_file(self.svc_file_dest)
        shutil.move(self.svc_file_path, self.svc_file_dest)
        if self.params.get('env'):
            self.lgr.debug('Deploying {0} to {1}...'.format(
                self.env_file_path, self.env_file_dest))
            self.create_system_directory_for_file(self.env_file_dest)
            shutil.move(self.env_file_path, self.env_file_dest)

        sh.systemctl.enable(self.name)

    def start(self):
        """Starts the service"""
        sh.systemctl.start(self.name)

    def stop(self):
        try:
            sh.systemctl.stop(self.name)
        except sh.ErrorReturnCode_5:
            self.lgr.debug('Service not running.')

    # TODO: this should be a decorator under base.py to allow
    # cleanup on failed creation.
    def uninstall(self):
        self.lgr.debug('Removing SystemD Service.')
        sh.systemctl.disable(self.name)
        if os.path.isfile(self.svc_file_dest):
            os.remove(self.svc_file_dest)
        if os.path.isfile(self.env_file_dest):
            os.remove(self.env_file_dest)

    def is_exist(self):
        return True if os.path.isfile(self.svc_file_dest) else False

    def status(self, name=''):
        svc_list = sh.systemctl('--no-legend', '--no-pager', t='service')
        svcs_info = [self._parse_service_info(svc) for svc in svc_list]
        if name:
            names = (name, name + '.service')
            # return list of one item for specific service
            svcs_info = [s for s in svcs_info if s['name'] in names]
        self.services.update({'services': svcs_info})
        return self.services

    @staticmethod
    def _parse_service_info(svc):
        svc_info = svc.split()
        return dict(
            name=svc_info[0],
            load=svc_info[1],
            active=svc_info[2],
            sub=svc_info[3],
            description=svc_info[4]
        )

    def _validate_init_system_specific_params(self):
        if not self.cmd.startswith('/'):
            self.lgr.error('SystemD requires the full path to the executable. '
                           'Instead, you provided: {0}'.format(self.cmd))
            sys.exit()
