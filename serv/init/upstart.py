import os
import re
import sys

from serv import utils
from serv.init.base import Base
from serv import constants as const

if not utils.IS_WIN:
    import sh


class Upstart(Base):
    def __init__(self, lgr=None, **params):
        super(Upstart, self).__init__(lgr=lgr, **params)

        if self.name:
            self.svc_file_dest = os.path.join(
                const.UPSTART_SVC_PATH, self.name + '.conf')

    def generate(self, overwrite=False):
        """Generates a config file for an upstart service.
        """
        super(Upstart, self).generate(overwrite=overwrite)

        svc_file_template = self.template_prefix + '.conf'
        self.svc_file_path = self.generate_into_prefix + '.conf'

        self.generate_file_from_template(svc_file_template, self.svc_file_path)
        return self.files

    def install(self):
        """Enables the service"""
        super(Upstart, self).install()

        self.deploy_service_file(self.svc_file_path, self.svc_file_dest)

    def start(self):
        """Starts the service"""
        try:
            sh.start(self.name)
        except:
            self.lgr.info('Service already started.')

    def stop(self):
        try:
            sh.stop(self.name)
        except:
            self.lgr.info('Service already stopped.')

    def uninstall(self):
        if os.path.isfile(self.svc_file_dest):
            os.remove(self.svc_file_dest)

    def status(self, name=''):
        super(Upstart, self).status(name=name)

        svc_list = sh.initctl.list()
        svcs_info = [self._parse_service_info(svc) for svc in svc_list]
        if name:
            # return list of one item for specific service
            svcs_info = [s for s in svcs_info if s['name'] == name]
        self.services['services'] = svcs_info
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

    def is_system_exists(self):
        try:
            sh.initctl.version()
            return True
        except:
            return False

    def get_system_version(self):
        try:
            output = sh.initctl.version()
        except:
            return
        version = re.search(r'(\d+((.\d+)+)+?)', str(output))
        if version:
            return str(version.group())
        return ''

    def is_service_exists(self):
        return os.path.isfile(self.svc_file_dest)

    def validate_platform(self):
        if utils.IS_WIN or utils.IS_DARWIN:
            self.lgr.error(
                'Cannot install SysVinit service on non-Linux systems.')
            sys.exit()
