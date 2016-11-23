import time
import shutil
import socket
import subprocess
from distutils.spawn import find_executable

import pytest

from serv import init
from serv import utils

from .test_serv import _invoke


class TestDeployReal:
    service_name = 'testservice'
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def _verify_port_open(self):
        # for some reason, socket does a bad job identifying opened
        # and closed ports here. weird.
        time.sleep(1)
        if utils.IS_WIN:
            assert self.sock.connect_ex(('127.0.0.1', 8000)) == 0
        else:
            subprocess.check_call(
                'ss -lnpt | grep 8000', shell=True, stdout=subprocess.PIPE)

    def _verify_port_closed(self):
        time.sleep(1)
        if utils.IS_WIN:
            assert self.sock.connect_ex(('127.0.0.1', 8000)) == 10056
        else:
            try:
                subprocess.check_call(
                    'ss -lnpt | grep 8000', shell=True, stdout=subprocess.PIPE)
            except subprocess.CalledProcessError as ex:
                assert 'returned non-zero exit status 1' in str(ex)

    def _test_deploy_remove(self, system):
        if system == 'nssm':
            executable = find_executable('python') or 'c:\\python27\\python'
        else:
            executable = find_executable('python2') or '/usr/bin/python2'

        _invoke('generate "{0}" -n {1} -a "-m SimpleHTTPServer" -d '
                '-s -v --overwrite --init-system {2}'.format(
                    executable, self.service_name, system))

        try:
            self._verify_port_open()
            if not utils.IS_WIN:
                _invoke('stop {0} --init-system {1}'.format(
                    self.service_name, system))
                self._verify_port_closed()
                _invoke('start {0} --init-system {1}'.format(
                    self.service_name, system))
                self._verify_port_open()
                _invoke('restart {0} --init-system {1}'.format(
                    self.service_name, system))
                self._verify_port_open()
            _invoke('remove {0} --init-system {1}'.format(
                self.service_name, system))
            self._verify_port_closed()
        finally:
            shutil.rmtree(
                utils.get_tmp_dir(system, self.service_name),
                ignore_errors=True)

    @pytest.mark.skipif(
        not init.systemd.is_system_exists(),
        reason='Systemd not found on this system.')
    @pytest.mark.skipif(utils.IS_WIN, reason='Irrelevant on Windows')
    def test_systemd(self):
        self._test_deploy_remove('systemd')

    @pytest.mark.skipif(
        not init.upstart.is_system_exists(),
        reason='Upstart not found on this system.')
    @pytest.mark.skipif(utils.IS_WIN, reason='Irrelevant on Windows')
    def test_upstart(self):
        self._test_deploy_remove('upstart')

    @pytest.mark.skipif(
        not init.sysv.is_system_exists(),
        reason='SysV not found on this system.')
    @pytest.mark.skipif(utils.IS_WIN, reason='Irrelevant on Windows')
    def test_sysv(self):
        self._test_deploy_remove('sysv')

    @pytest.mark.skipif(utils.IS_LINUX, reason='Irrelevant on Linux')
    def test_nssm(self):
        self._test_deploy_remove('nssm')
