import os
import sys
import shutil

from serv.init.base import Base
from serv import constants as const
from serv import utils


RUNNING_STATES = ['SERVICE_RUNNING', 'SERVICE_STOP_PENDING']


class Nssm(Base):
    def __init__(self, lgr=None, **params):
        super(Nssm, self).__init__(lgr=lgr, **params)
        # raise NotImplementedError('nssm is not ready yet. Come back soon...')
        if self.name:
            self.svc_file_dest = os.path.join(
                const.NSSM_SVC_PATH, self.name + '.bat')
        self.nssm_exe = os.path.join(const.NSSM_BINARY_PATH, 'nssm.exe')

    def generate(self, overwrite=False):
        super(Nssm, self).generate(overwrite=overwrite)
        self._set_init_system_specific_params()

        svc_file_template = self.template_prefix + '.bat'
        self.svc_file_path = self.generate_into_prefix + '.bat'

        self.generate_file_from_template(svc_file_template, self.svc_file_path)
        return self.files

    def install(self):
        super(Nssm, self).install()

        self.deploy_service_file(
            self.svc_file_path, self.svc_file_dest, create_directory=True)

        if not os.path.isfile(self.nssm_exe):
            self._deploy_nssm_binary()
        utils.run(self.svc_file_dest)

    def start(self):
        utils.run('sc start {0}'.format(self.name))

    def stop(self):
        utils.run('sc stop {0}'.format(self.name))

    # TODO: this should be a decorator under base.py to allow
    # cleanup on failed creation.
    def uninstall(self):
        utils.run('sc config {0} start= disabled'.format(self.name))
        utils.run('{0} remove {1} confirm'.format(self.nssm_exe, self.name))
        if os.path.isfile(self.svc_file_dest):
            os.remove(self.svc_file_dest)

    def status(self, name):
        super(Nssm, self).status(name=name)

        _, result, _ = self.nssm('status')
        # apparently nssm output is encoded in utf16.
        # encode to ascii to be able to parse this
        state = result.decode('utf16').encode('utf-8').rstrip()
        self.services.update(
            {'services': [dict(name=self.name, status=state)]})
        return self.services

    def is_system_exists(self):
        """Returns True always since if it isn't installed, it will be.

        See `self.install`
        """
        return True

    def is_service_exists(self):
        code, _, _ = utils.run('sc query {0}'.format(self.name))
        if code != 0:
            return False
        return True

    def nssm(self, cmd):
        return utils.run('{0} {1} {2}'.format(self.nssm_exe, cmd, self.name))

    def _deploy_nssm_binary(self):
        # still not sure whether we should use this or
        # is_pyx32 = True if struct.calcsize("P") == 4 else False
        # TODO: check what checks for OS arch and which checks Python arch.
        is_64bits = sys.maxsize > 2 ** 32
        binary = 'nssm64.exe' if is_64bits else 'nssm32.exe'
        source = os.path.join(os.path.dirname(__file__), 'binaries', binary)
        if not os.path.isdir(const.NSSM_BINARY_PATH):
            os.makedirs(const.NSSM_BINARY_PATH)
        self.lgr.debug('Deploying {0} to {1}...'.format(source, self.nssm_exe))
        shutil.copyfile(source, self.nssm_exe)
        return self.nssm_exe

    def _set_init_system_specific_params(self):
        # should of course be configurable
        self.params.update({
            'startup_policy': 'auto',
            'failure_reset_timeout': 60,
            'failure_restart_delay': 5000,
            'nssm_dir': const.NSSM_BINARY_PATH
        })

    def validate_platform(self):
        if not utils.IS_WIN:
            self.lgr.error(
                'Cannot install nssm service on non-Windows systems.')
            sys.exit()
