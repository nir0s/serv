import socket
import time

import click.testing as clicktest
import testtools

import serv.serv as serv


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


class TestServ(testtools.TestCase):

    def setUp(self):
        super(TestServ, self).setUp()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def _verify_port_open(self):
        # exponential backoff instead
        time.sleep(3)
        self.assertEqual(self.sock.connect_ex(('127.0.0.1', 8000)), 0)

    def _verify_port_closed(self):
        self.assertEqual(self.sock.connect_ex(('127.0.0.1', 8000)), 106)

    def _test_generate_remove(self, system):
        service_name = 'test'
        args = ['/usr/bin/python2']
        opts = {
            '-n': service_name,
            '-a': '-m SimpleHTTPServer',
            '-d': None,
            '-s': None,
            '-v': None,
            '--init-system=': system
        }

        _invoke_click('generate', args, opts)
        self._verify_port_open()
        _invoke_click('remove', args=[service_name])
        self._verify_port_closed()

    def test_systemd(self):
        if serv.IS_WIN:
            self.skipTest('Irrelevant on Windows.')
        self._test_generate_remove('systemd')

    # def test_upstart(self):
    #     if serv.IS_WIN:
    #         self.skipTest('Irrelevant on Windows.')
    #     self._test_generate_remove('upstart')

    # def test_sysv(self):
    #     if serv.IS_WIN:
    #         self.skipTest('Irrelevant on Windows.')
    #     self._test_generate_remove('sysv')

    # def test_nssm(self):
    #     if serv.IS_LINUX:
    #         self.skipTest('Irrelevant on Linux.')
    #     self._test_generate_remove('nssm')
