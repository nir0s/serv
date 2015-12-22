import os
import shutil

import sh

from serv.init.base import Base
from serv import constants as const


class Upstart(Base):
    def __init__(self, lgr=None, **params):
        super(Upstart, self).__init__(lgr=lgr, **params)
        if self.name:
            self.svc_file_dest = os.path.join(
                const.UPSTART_SCRIPT_PATH, self.name + '.conf')

    def generate(self, overwrite=False):
        """Generates a config file for an upstart service.
        """
        super(Upstart, self).generate(overwrite=overwrite)

        self.lgr.debug('Generating Service files.')
        svc_file_tmplt = '{0}_{1}.conf.j2'.format(
            self.init_sys, self.init_sys_ver)

        self.svc_file_path = os.path.join(self.tmp, self.name)

        files = [self.svc_file_path]

        self.generate_file_from_template(
            svc_file_tmplt, self.svc_file_path, self.params, overwrite)

        return files

    def install(self):
        """Enables the service"""
        super(Upstart, self).install()

        self.lgr.debug('Deploying {0} to {1}...'.format(
            self.svc_file_path, self.svc_file_dest))
        self.create_system_directory_for_file(self.svc_file_dest)
        shutil.move(self.svc_file_path, self.svc_file_dest)

    def start(self):
        """Starts the service"""
        sh.start(self.name)

    def stop(self):
        sh.stop(self.name)

    def uninstall(self):
        os.remove(self.svc_file_dest)

    def is_exist(self):
        return True if os.path.isfile(self.svc_file_dest) else False

    def status(self, name=''):
        svc_list = sh.initctl.list()
        svcs_info = [self._parse_service_info(svc) for svc in svc_list]
        if name:
            # return list of one item for specific service
            svcs_info = [s for s in svcs_info if s['name'] == name]
        self.services.update({'services': svcs_info})
        return self.services

    @staticmethod
    def _parse_service_info(svc):
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
