import os
import shutil
import tempfile

from serv import utils
from serv.exceptions import ServError

from serv.init.base import Base


MOCK_INIT_SYSTEM_DIR = os.path.join(tempfile.gettempdir(), 'mock-test-system')


class MockSystem(Base):
    def __init__(self, logger=None, **params):
        super(MockSystem, self).__init__(logger=logger, **params)

        if self.name:
            self.svc_file_dest = os.path.join(MOCK_INIT_SYSTEM_DIR, self.name)
            self.started_file = self.svc_file_dest + '.started'

    def generate(self, overwrite=False):
        super(MockSystem, self).generate(overwrite=overwrite)

        self.svc_file_path = self.generate_into_prefix + '.service'

        with open(self.svc_file_path, 'w') as service_file:
            service_file.write('mock_service_file')
        return [self.svc_file_path]

    def install(self):
        super(MockSystem, self).install()

        self.deploy_service_file(
            self.svc_file_path,
            self.svc_file_dest,
            create_directory=True)

    def start(self):
        shutil.copy2(self.svc_file_dest, self.started_file)

    def stop(self):
        if os.path.isfile(self.started_file):
            os.remove(self.started_file)

    def uninstall(self):
        if os.path.isfile(self.svc_file_dest):
            os.remove(self.svc_file_dest)

    def status(self, name=''):
        super(MockSystem, self).status(name=name)
        self.services.update(services=[])
        self.services['services'].append(dict(
            started=os.path.isfile(self.started_file),
            installed=os.path.isfile(self.svc_file_dest),
            name=name))
        return self.services

    @staticmethod
    def is_system_exists():
        return True

    def is_service_exists(self):
        return os.path.isfile(self.svc_file_dest)

    def validate_platform(self):
        if utils.IS_WIN or utils.IS_DARWIN:
            raise ServError(
                'Cannot install Mock service on non-Linux systems.')
