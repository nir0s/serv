import os
import sh
import shutil

from StringIO import StringIO

from serv.init.base import Base
from serv import constants as const


class Runit(Base):

    def __init__(self, lgr, **params):
        super(Runit, self).__init__(lgr=lgr, **params)
        if self.name:
            self.svc_file_dest = os.path.join(const.RUNIT_SCRIPT_PATH,
                                              self.name)
        self.svc_temp_dir_path = os.path.join(self.tmp, self.name)
        self.svc_file_path = os.path.join(self.svc_temp_dir_path, 'run')

    def generate(self, overwrite):
        super(Runit, self).generate(overwrite=overwrite)

        svc_file_tmplt = '{0}_{1}.service.j2'.format(
            self.init_sys, self.init_sys_ver)

        os.makedirs(self.svc_temp_dir_path)
        self.generate_file_from_template(svc_file_tmplt, self.svc_file_path)
        os.chmod(self.svc_file_path, 777)

        return [self.svc_file_path]

    def install(self):
        super(Runit, self).install()

        os.makedirs(self.svc_file_dest)
        shutil.copy(self.svc_file_path, self.svc_file_dest)
        self._execute_with_retry(sh.sv.down, func_args={self.name})

    def start(self):
        self._execute_with_retry(sh.sv.up, func_args={self.name})

    def stop(self):
        sh.sv.down(self.name)
        shutil.rmtree(self.svc_temp_dir_path, ignore_errors=True)

    def uninstall(self):
        shutil.rmtree(self.svc_file_dest, ignore_errors=True)

    def status(self, name=''):
        super(Runit, self).status(name=name)
        stdout = StringIO()
        sh.sv.status(self.name, _out=stdout)
        self.services['services'].append(
                {name: self._parse_runit_output(stdout, name)}
        )
        return self.services

    def is_system_exists(self):
        try:
            sh.runit
            return True
        except:
            return False

    def is_service_exists(self):
        try:
            sh.sv.status(self.name)
            return True
        except:
            return False

    @staticmethod
    def _parse_runit_output(stdout, name):

        out = stdout.getvalue()
        general_status, info = out.split(':', 1)
        info = [i.strip() for i in info.split(',')[1:]]
        status = {stat.split(' ')[0]: stat.split(' ')[1] for stat in info}
        status.update({
            'status': general_status.strip()
        })
        return status
