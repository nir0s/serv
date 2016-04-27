
import os
from shutil import rmtree
from time import sleep
from ConfigParser import ConfigParser
from collections import namedtuple

import sh

from .base import Base


class Supervisor(Base):
    CONFIG_FILE_EXTENSION = '.conf'
    SUPERVISOR_OFFLINE = 'offline_status'
    SUPERVISOR_ONLINE = 'online_status'
    _STATUS_INTERVAL = xrange(10)
    ProcessStatus = namedtuple(
        'ProcessStatus', 'process, status, pid, uptime')

    def __init__(self, lgr=None, **params):
        """

        :param lgr:
        :param params:
        """
        super(Supervisor, self).__init__(lgr=lgr, **params)
        self._create_configuration_object()

    def status(self, name=''):
        for _ in self._STATUS_INTERVAL:
            output = self._client(action='status', process=name)
            if output and name in output:
                break
            sleep(1)
        else:
            raise Exception(
                'Supervisor service: {0}, '
                'failed to get status'.format(self.name))
        if any(('refused connection' in output,
                'no such file' in output)):
            return self.SUPERVISOR_OFFLINE

        print name, '1'*30
        if name:
            for line in output.splitlines():
                process_status = self._parse_stdout_line_to_status(line)
                print process_status, '2' * 30
                if process_status.process == name:
                    return process_status
        return self.SUPERVISOR_ONLINE

    def generate(self, overwrite):
        super(Supervisor, self).generate(overwrite)
        self.generate_file_from_template(
            template=self.template_prefix,
            destination=self.generate_into_prefix)
        return self.files

    def install(self):
        self.deploy_service_file(
            source=self.generate_into_prefix,
            destination=self._service_config_file())
        self._client('update')
        self.status(self.name)

    def uninstall(self):
        rmtree(self._service_config_file(), ignore_errors=True)
        self._client('update')

    def start(self):
        self._client('start', self.name)
        for _ in self._STATUS_INTERVAL:
            process_status = self.status(self.name)
            print process_status, '0'*30
            if process_status.status == 'RUNNING':
                return
        raise Exception('failed to start service: {0}'.format(self.name))

    def stop(self):
        self._client('stop', self.name)
        for _ in self._STATUS_INTERVAL:
            process_status = self.status(self.name)
            if process_status.status == 'STOPPED':
                return
        raise Exception('failed to stop service: {0}'.format(self.name))

    def is_system_exists(self):
        return self.status() == self.SUPERVISOR_ONLINE

    def validate_platform(self):
        pass

    def is_service_exists(self):
        if isinstance(self.status(self.name), self.ProcessStatus):
            return True
        return False

    def _create_configuration_object(self):
        self._configuration = ConfigParser()
        self._configuration.read(self.params['supervisor_config'])
        glob_paths = self._configuration.get('include', 'files').split()
        for glob_path in glob_paths:
            if os.path.exists(glob_path):
                continue
            path, extention = glob_path.split('*')
            break
        else:
            raise Exception(
                'Supervisor config file dos not support '
                'extra include files.')
        (self._include_path,
         self._config_files_extention) = (
            path, extention or self.CONFIG_FILE_EXTENSION)

    def _client(self, action, process=''):
        try:
            return sh.supervisorctl(
                '-c', self.params['supervisor_config'],
                action, process)
        except:
            self.lgr.error('supervisor client faild to connect')
            return None

    def _parse_stdout_line_to_status(self, line):
        column = line.split()
        return self.ProcessStatus(
            process=column[0],
            status=column[1],
            pid=column[3] if column[1] == 'RUNNING' else None,
            uptime=column[5] if column[1] == 'RUNNING' else None,
        )

    def _service_config_file(self):
        return os.path.join(
            self._include_path,
            self.name + self._config_files_extention)
