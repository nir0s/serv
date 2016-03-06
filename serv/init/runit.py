import os

import sh
import shutil

from serv.init.base import Base
from serv import constants as const


class Runit(Base):

    def __init__(self, lgr, **params):
        super(Runit, self).__init__(lgr=lgr, **params)
        if self.name:
            self.svc_file_dest = os.path.join(const.RUNIT_SCRIPT_PATH,
                                              self.name)

    def generate(self, overwrite):
        super(Runit, self).generate(overwrite=overwrite)

        svc_file_tmplt = '{0}_{1}.service.j2'.format(
            self.init_sys, self.init_sys_ver)

        self.svc_file_path = os.path.join(self.tmp, self.name, 'run')
        os.makedirs(os.path.join(self.tmp, self.name))

        self.generate_file_from_template(svc_file_tmplt, self.svc_file_path)
        os.chmod(self.svc_file_path, 777)

        return [self.svc_file_path]

    def install(self):
        # TODO: is this really needed
        # super(Runit, self).install()

        os.makedirs(self.svc_file_dest)
        shutil.copy(self.svc_file_path, self.svc_file_dest)
        sh.sv(self.name, 'stop', _bg=True)
        pass

    def start(self):
        sh.sv.start(self.name)

    def stop(self):
        sh.sv.stop(self.name)

    def uninstall(self):
        sh.sv.stop(self.name)
        shutil.rmtree(os.path.join(self.svc_file_dest, self.name))

    def status(self, name=''):
        sh.sv.status(self.name)
        pass

    def is_system_exists(self):
        try:
            sh.runit
            return True
        except:
            return False

    def is_service_exists(self):
        pass
