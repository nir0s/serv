
import os
import sys
from ConfigParser import ConfigParser

import sh

from .base import Base


class Supervisor(Base):
    CONFIG_FILE_EXTENTION = '.conf'
    SUPERVISOR_OFFLINE = 'offline_status'

    def __init__(self, lgr=None, **params):
        """

        :param lgr:
        :param params:
        """
        super(Supervisor, self).__init__(lgr=lgr, **params)
        self._create_configuration_object()

    def _create_configuration_object(self):
        self._configuration = ConfigParser()
        self._configuration.read(self.params['supervisor_config'])

    def _include_directory(self):
        glob_paths = self._configuration.get('include', 'files').split()
        for glob_path in glob_paths:
            if os.path.exists(glob_path):
                continue
            path, extention = glob_path.split('*')
            return path, extention or self.CONFIG_FILE_EXTENTION
        raise Exception('Supervisor config file dos not support '
                        'extra include files.')

    def _client(self, action, process=''):
        return sh.supervisorctl(
            '-c', self.params['supervisor_config'], action, process)

    def _analyze_output_iter(self, output):
        for line in output.splitlines():
            for column in line.split():
                if len(column) < 4:
                    yield None
                yield {
                    'process': column[0],
                    'status': column[1],
                    'pid': column[3] if column[1] == 'RUNNING' else None,
                    'uptime': column[5] if column[1] == 'RUNNING' else None,
                }

    def status(self, name=''):
        output = self._client(action='status', process=name)
        if 'refused connection' in output:
            return self.SUPERVISOR_OFFLINE
        return next(self._analyze_output_iter(output))

    def generate(self, overwrite):
        super(Supervisor, self).generate(overwrite)
        path, extention = self._include_directory()
        self.generate_file_from_template(
            template=self.template_prefix,
            destination=os.path.join(path, self.name + extention))
        return self.files

    def install(self):
        self._client('update')

    def uninstall(self):
        pass

    def start(self):
        self._client('start', self.name)

    def stop(self):
        self._client('stop', self.name)

    def is_system_exists(self):
        return not self.status() == self.SUPERVISOR_OFFLINE

    def validate_platform(self):
        pass
