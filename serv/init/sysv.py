import os
import subprocess

from .. import utils
from .. import constants
from ..exceptions import ServError

from .base import Base

if not utils.IS_WIN:
    import sh


class SysV(Base):
    def __init__(self, logger=None, **params):
        super(SysV, self).__init__(logger=logger, **params)

        if self.name:
            self.svc_file_dest = os.path.join(
                constants.SYSV_SVC_PATH, self.name)
            self.env_file_dest = os.path.join(
                constants.SYSV_ENV_PATH, self.name + '.defaults')

    def generate(self, overwrite=False):
        super(SysV, self).generate(overwrite=overwrite)
        self._set_init_system_specific_params()

        svc_file_template = self.template_prefix
        env_file_template = self.template_prefix + '.defaults'
        self.svc_file_path = self.generate_into_prefix
        self.env_file_path = self.generate_into_prefix + '.defaults'

        self.generate_file_from_template(svc_file_template, self.svc_file_path)
        self.generate_file_from_template(env_file_template, self.env_file_path)
        return self.files

    def install(self):
        super(SysV, self).install()

        self.deploy_service_file(self.svc_file_path, self.svc_file_dest)
        self.deploy_service_file(self.env_file_path, self.env_file_dest)

        os.chmod(self.svc_file_dest, 755)

    def start(self):
        try:
            subprocess.check_call(
                'service {0} start'.format(self.name),
                shell=True, stdout=subprocess.PIPE)
        except sh.CommandNotFound:
            # TODO: cleanup generated files if not found.
            self.logger.warning(
                'service command unavailable. Trying to run script directly.')
            try:
                service = sh.Command('/etc/init.d/{0}'.format(self.name))
                service.start(_bg=True)
            except sh.CommandNotFound as ex:
                raise ServError('Command not found: {0}'.format(ex))
        except:
            self.logger.info('Service already started.')

    def stop(self):
        try:
            subprocess.check_call(
                'service {0} stop'.format(self.name),
                shell=True, stdout=subprocess.PIPE)
        except sh.CommandNotFound:
            self.logger.warning(
                'service command unavailable. Trying to run script directly.')
            try:
                service = sh.Command('/etc/init.d/{0}'.format(self.name))
                service.stop(_bg=True)
            except sh.CommandNotFound as ex:
                raise ServError('Command not found: {0}'.format(ex))
        except:
            self.logger.info('Service already stopped.')

    def uninstall(self):
        if os.path.isfile(self.svc_file_dest):
            os.remove(self.svc_file_dest)
        if os.path.isfile(self.env_file_dest):
            os.remove(self.env_file_dest)

    def status(self, name=''):
        """WIP!"""
        raise NotImplementedError()

    @staticmethod
    def is_system_exists():
        return is_system_exists()

    def is_service_exists(self):
        return os.path.isfile(self.svc_file_dest)

    def _set_init_system_specific_params(self):
        # TODO: figure out if to depracate these two.
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

    def validate_platform(self):
        if utils.IS_WIN or utils.IS_DARWIN:
            raise ServError(
                'Cannot install SysVinit service on non-Linux systems.')


def is_system_exists():
    # TODO: maybe a safer way would be to check if /etc/init.d is not empty.
    return os.path.isdir('/etc/init.d')
