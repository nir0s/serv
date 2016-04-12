import socket
import time
import os
import shutil
import getpass
from distutils.spawn import find_executable

import click.testing as clicktest
import testtools

import serv.serv as serv
from serv import utils


def _invoke_click(func, args=None, opts=None):

    args = args or []
    opts = opts or {}
    opts_and_args = []
    opts_and_args.extend(args)
    for opt, value in opts.items():
        if value:
            opts_and_args.append(opt + value)
        else:
            opts_and_args.append(opt)
    return clicktest.CliRunner().invoke(getattr(serv, func), opts_and_args)


class TestGenerate(testtools.TestCase):

    def setUp(self):
        super(TestGenerate, self).setUp()
        self.service = 'testservice'
        self.nssm = self.service + '.bat'
        self.systemd = self.service + '.service'
        self.upstart = self.service + '.conf'
        self.sysv = self.service

    def _get_file_for_system(self, system):
        return os.path.join(
            utils.get_tmp_dir(system, self.service), getattr(self, system))

    def _test_generate(self, sys):
        if sys == 'nssm':
            self.cmd = find_executable('python') or 'c:\\python27\\python'
        else:
            self.cmd = find_executable('python2') or '/usr/bin/python2'
        self.args = '-m SimpleHTTPServer'
        opts = {
            '-n': self.service,
            '-a': self.args,
            '-v': None,
            '--overwrite': None,
            '--init-system=': sys
        }
        try:
            _invoke_click('generate', [self.cmd], opts)
            f = self._get_file_for_system(sys)
            self.assertTrue(f)
            with open(f) as generated_file:
                self.content = generated_file.read()
        finally:
            shutil.rmtree(os.path.dirname(f))

    def test_systemd(self):
        self._test_generate('systemd')
        self.assertIn(self.cmd + ' ' + self.args, self.content)

    def test_upstart(self):
        self._test_generate('upstart')
        self.assertIn(self.cmd + ' ' + self.args, self.content)

    def test_sysv(self):
        self._test_generate('sysv')
        self.assertIn('program={0}'.format(self.cmd), self.content)
        self.assertIn('args="{0}"'.format(self.args), self.content)

    def test_nssm(self):
        self._test_generate('nssm')
        self.assertIn(
            '"{0}" "{1}" "{2}"'.format(self.service, self.cmd, self.args),
            self.content)

    def test_generate_no_overwrite(self):
        sys = 'systemd'
        cmd = find_executable('python2') or '/usr/bin/python2'
        opts = {
            '-n': self.service,
            '--init-system=': sys
        }
        try:
            _invoke_click('generate', [cmd], opts)
            r = _invoke_click('generate', [cmd], opts)
            self.assertEqual(r.exit_code, 1)
            f = self._get_file_for_system(sys)
            self.assertIn('File already exists: {0}'.format(f), r.output)
        finally:
            shutil.rmtree(os.path.dirname(f))

    def test_bad_string_limit_value(self):
        sys = 'systemd'
        cmd = '/usr/bin/python2'
        opts = {
            '-n': self.service,
            '-v': None,
            '--overwrite': None,
            '--init-system=': sys,
            '--limit-coredump=': 'asd'
        }
        r = _invoke_click('generate', [cmd], opts)
        self.assertIn('All limits must be integers', r.output)

    def test_bad_negative_int_limit_value(self):
        sys = 'systemd'
        cmd = find_executable('python2') or '/usr/bin/python2'
        opts = {
            '-n': self.service,
            '-v': None,
            '--overwrite': None,
            '--init-system=': sys,
            '--limit-stack-size=': '-10'
        }
        r = _invoke_click('generate', [cmd], opts)
        self.assertIn('All limits must be integers', r.output)


class TestDeploy(testtools.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.service_name = 'test'
        cls.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def tearDown(self):
        super(TestDeploy, self).tearDown()
        _invoke_click('remove', args=[self.service_name])

    def _verify_port_open(self):
        time.sleep(3)
        self.assertEqual(self.sock.connect_ex(('127.0.0.1', 8000)), 0)

    def _verify_port_closed(self):
        self.assertEqual(self.sock.connect_ex(('127.0.0.1', 8000)),
                         10056 if utils.IS_WIN else 106)

    def _test_deploy_remove(self, system):
        if system == 'nssm':
            args = find_executable('python') or 'c:\\python27\\python'
        else:
            args = find_executable('python2') or '/usr/bin/python2'
        opts = {
            '-n': self.service_name,
            '-a': '-m SimpleHTTPServer',
            '-d': None,
            '-s': None,
            '-v': None,
            '--overwrite': None,
            '--init-system=': system
        }

        _invoke_click('generate', [args], opts)
        self._verify_port_open()
        _invoke_click('remove', args=[self.service_name])
        self._verify_port_closed()

    # TODO: these should all use init.is_system_exists to check whether
    # a test can run or not. this is just silly.
    def test_systemd(self):
        if utils.IS_WIN:
            self.skipTest('Irrelevant on Windows.')
        if getpass.getuser() != 'travis':
            self.skipTest('Cannot run on Travis.')
        self._test_deploy_remove('systemd')

    def test_upstart(self):
        if utils.IS_WIN:
            self.skipTest('Irrelevant on Windows.')
        if getpass.getuser() != 'travis':
            self.skipTest('Should run on Travis.')
        self._test_deploy_remove('upstart')

    def test_sysv(self):
        if utils.IS_WIN:
            self.skipTest('Irrelevant on Windows.')
        if getpass.getuser() == 'travis':
            self.skipTest('Should run on Travis.')
        self._test_deploy_remove('sysv')

    def test_nssm(self):
        if utils.IS_LINUX:
            self.skipTest('Irrelevant on Linux.')
        self._test_deploy_remove('nssm')
