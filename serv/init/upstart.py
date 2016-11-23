import os

from .. import utils
from .. import constants
from ..exceptions import ServError

from .base import Base

if not utils.IS_WIN:
    import sh


class Upstart(Base):
    def __init__(self, logger=None, **params):
        super(Upstart, self).__init__(logger=logger, **params)

        if self.name:
            self.svc_file_dest = os.path.join(
                constants.UPSTART_SVC_PATH, self.name + '.conf')

    def generate(self, overwrite=False):
        """Generate a config file for an upstart service.
        """
        super(Upstart, self).generate(overwrite=overwrite)

        svc_file_template = self.template_prefix + '.conf'
        self.svc_file_path = self.generate_into_prefix + '.conf'

        self.generate_file_from_template(svc_file_template, self.svc_file_path)
        return self.files

    def install(self):
        """Enable the service"""
        super(Upstart, self).install()

        self.deploy_service_file(self.svc_file_path, self.svc_file_dest)

    def start(self):
        """Start the service"""
        try:
            sh.start(self.name)
        except:
            self.logger.info('Service already started.')

    def stop(self):
        try:
            sh.stop(self.name)
        except:
            self.logger.info('Service already stopped.')

    def uninstall(self):
        if os.path.isfile(self.svc_file_dest):
            os.remove(self.svc_file_dest)

    def status(self, name=''):
        raise NotImplementedError()

    @staticmethod
    def is_system_exists():
        return is_system_exists()

    def is_service_exists(self):
        return os.path.isfile(self.svc_file_dest)

    def validate_platform(self):
        if utils.IS_WIN or utils.IS_DARWIN:
            raise ServError(
                'Cannot install Upstart service on non-Linux systems.')


def is_system_exists():
    try:
        sh.initctl.version()
        return True
    except sh.CommandNotFound:
        return False
