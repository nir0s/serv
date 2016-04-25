import os
import time
import socket
import shutil
import subprocess
from distutils.spawn import find_executable

import testtools
import click.testing as clicktest

from serv import utils
import serv.serv as serv

from serv import init


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

    def tearDown(self):
        super(TestGenerate, self).tearDown()
        # TODO: ignore_errors?
        try:
            shutil.rmtree(os.path.dirname(self.init_script))
        except:
            pass

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
        additional_opts = {
            '--nice=': '5',
            '--limit-coredump=': '10',
            '--limit-physical-memory=': '20',
            '--var=': 'KEY1=VALUE1'
        }
        opts.update(additional_opts)
        self.init_script = self._get_file_for_system(sys)
        _invoke_click('generate', [self.cmd], opts)
        self.assertTrue(self.init_script)
        with open(self.init_script) as generated_file:
            self.content = generated_file.read()

    def test_systemd(self):
        self._test_generate('systemd')
        self.assertIn(self.cmd + ' ' + self.args, self.content)

        self.assertIn('LimitNICE=5', self.content)
        self.assertIn('LimitCORE=10', self.content)
        self.assertIn('LimitRSS=20', self.content)
        env_vars_file = os.path.join(
            utils.get_tmp_dir('systemd', self.service), self.service)
        with open(env_vars_file) as vars_file:
            content = vars_file.read()
        self.assertIn('KEY1=VALUE1', content)

    def test_upstart(self):
        self._test_generate('upstart')
        self.assertIn(self.cmd + ' ' + self.args, self.content)

        self.assertIn('nice 5', self.content)
        self.assertIn('limit core 10 10', self.content)
        self.assertIn('limit rss 20 20', self.content)
        self.assertIn('env KEY1=VALUE1', self.content)

    def test_sysv(self):
        self._test_generate('sysv')
        self.assertIn('program={0}'.format(self.cmd), self.content)
        self.assertIn('args="{0}"'.format(self.args), self.content)
        self.assertIn('nice -n "$nice"', self.content)
        self.assertIn('ulimit -d 10 -m 20', self.content)
        env_vars_file = os.path.join(
            utils.get_tmp_dir('sysv', self.service),
            self.service + '.defaults')
        with open(env_vars_file) as vars_file:
            content = vars_file.read()
        self.assertIn('nice="5"', content)

    def test_nssm(self):
        self._test_generate('nssm')
        self.assertIn(
            '"{0}" "{1}" "{2}"'.format(self.service, self.cmd, self.args),
            self.content)
        self.assertIn('KEY1=VALUE1 ^', self.content)

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
        cls.service_name = 'testservice'
        cls.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def setUp(self):
        super(TestDeploy, self).setUp()

    def tearDown(self):
        super(TestDeploy, self).tearDown()

    def _verify_port_open(self):
        # for some reason, socket does a bad job identifying opened
        # and closed ports here. weird.
        time.sleep(1)
        if utils.IS_WIN:
            self.assertEqual(self.sock.connect_ex(('127.0.0.1', 8000)), 0)
        else:
            subprocess.check_call(
                'ss -lnpt | grep 8000', shell=True, stdout=subprocess.PIPE)

    def _verify_port_closed(self):
        time.sleep(1)
        if utils.IS_WIN:
            self.assertEqual(self.sock.connect_ex(('127.0.0.1', 8000)), 10056)
        else:
            try:
                subprocess.check_call(
                    'ss -lnpt | grep 8000', shell=True, stdout=subprocess.PIPE)
            except subprocess.CalledProcessError as ex:
                self.assertIn('returned non-zero exit status 1', str(ex))

    def _test_deploy_remove(self, system):
        if system == 'nssm':
            args = find_executable('python') or 'c:\\python27\\python'
        else:
            args = find_executable('python2') or '/usr/bin/python2'
        init_system = {'--init-system=': system}
        opts = {
            '-n': self.service_name,
            '-a': '-m SimpleHTTPServer',
            '-d': None,
            '-s': None,
            '-v': None,
            '--overwrite': None,
        }
        opts.update(init_system)

        _invoke_click('generate', [args], opts)
        self._verify_port_open()
        if not utils.IS_WIN:
            _invoke_click('stop', [self.service_name], init_system)
            self._verify_port_closed()
            _invoke_click('start', [self.service_name], init_system)
            self._verify_port_open()
            _invoke_click('restart', [self.service_name], init_system)
            self._verify_port_open()
        _invoke_click('remove', [self.service_name], init_system)
        self._verify_port_closed()

    def test_systemd(self):
        if utils.IS_WIN:
            self.skipTest('Irrelevant on Windows.')
        if not init.systemd.is_system_exists():
            self.skipTest('Systemd not found on this system.')
        self._test_deploy_remove('systemd')

    def test_upstart(self):
        if utils.IS_WIN:
            self.skipTest('Irrelevant on Windows.')
        if not init.upstart.is_system_exists():
            self.skipTest('Upstart not found on this system.')
        self._test_deploy_remove('upstart')

    def test_sysv(self):
        if utils.IS_WIN:
            self.skipTest('Irrelevant on Windows.')
        if not init.sysv.is_system_exists():
            self.skipTest('SysVinit not found on this system.')
        self._test_deploy_remove('sysv')

    def test_nssm(self):
        if utils.IS_LINUX:
            self.skipTest('Irrelevant on Linux.')
        self._test_deploy_remove('nssm')
