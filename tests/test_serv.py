import os
import shlex
import shutil
from distutils.spawn import find_executable

try:
    import distro
except ImportError:
    pass
import mock
import pytest
import click.testing as clicktest

import serv.serv as serv
from serv import utils
from serv import exceptions

# TODO: Consolidate all find_executable's


if not utils.IS_WIN:
    print('DISTRIBUTION INFO: {0}'.format(distro.info()))


def _invoke(command):
    cli = clicktest.CliRunner()

    lexed_command = command if isinstance(command, list) \
        else shlex.split(command)
    func = lexed_command[0]
    params = lexed_command[1:]
    return cli.invoke(getattr(serv, func), params)


class TestGeneral:
    @pytest.mark.skipif(utils.IS_WIN, reason='Irrelevant on Windows')
    def test_utils_run(self):
        returncode, output, _ = utils.run('uname')
        assert returncode == 0
        assert output.decode('utf-8') == 'Linux'

    def test_provide_supported_init_system(self):
        client = serv.Serv('systemd')
        assert client.init_system == 'systemd'

    def test_identify_init_system(self):
        client = serv.Serv()
        assert client.init_system

    def test_provide_unsupported_init_system(self):
        with pytest.raises(exceptions.ServError) as ex:
            serv.Serv('unsupported_init_sys')
        assert 'Init system unsupported_init_sys not supported' in str(ex)

    @mock.patch.object(serv.Serv, 'lookup_init_systems')
    def test_unable_to_detect_init_system(self, _lookup):
        _lookup.return_value = None
        with pytest.raises(exceptions.ServError) as ex:
            serv.Serv()
        assert 'No init system detected' in str(ex)

    def test_parse_service_env_vars(self):
        client = serv.Serv('systemd')
        parsed = client._parse_service_env_vars(('a=b', 'b=c'))
        expected = {'a': 'b', 'b': 'c'}
        assert parsed == expected

    def test_set_service_name_from_command(self):
        client = serv.Serv('systemd')
        name = client._set_service_name_from_command('/path/to/command')
        assert name == 'command'

    def test_assert_service_not_installed(self):
        name = 'testservice'
        client = serv.Serv()
        init = client._get_implementation(name)
        with pytest.raises(exceptions.ServError) as ex:
            client._assert_service_installed(init, name)
        assert 'does not seem to be installed' in str(ex)

    def _test_init_system_lookup(self, method):
        client = serv.Serv()
        available_init_systems = getattr(client, method)()
        assert len(available_init_systems) > 0
        assert all(sys in serv.INIT_SYSTEM_MAPPING.keys()
                   for sys in available_init_systems)
        return available_init_systems

    def test_init_systems_lookup(self):
        self._test_init_system_lookup('lookup_init_systems')

    def test_init_systems_lookup_by_mapping(self):
        systems = self._test_init_system_lookup('_lookup_by_mapping')
        assert len(systems) == 1

    def test_init_systems_lookup_automatically(self):
        self._test_init_system_lookup('_init_sys_auto_lookup')

    def test_init_systems_lookup_automatically_force_all(self):
        client = serv.Serv()
        with mock.patch.object(client, '_is_init_system_installed') as _lookup:
            _lookup.return_value = True
            available_init_systems = client._init_sys_auto_lookup()
            assert available_init_systems.sort() == \
                ['systemd', 'sysv', 'upstart'].sort()

    def _test_static_os_specific_init_systems(self, expected_systems):
        client = serv.Serv()
        available_init_systems = client.lookup_init_systems()
        assert available_init_systems == expected_systems

    @mock.patch('serv.utils.IS_WIN', return_value=True)
    def test_init_systems_lookup_force_windows(self, _):
        self._test_static_os_specific_init_systems(['nssm'])

    def test_init_systems_lookup_force_darwin(self):
        # Since launchd is not yet supported, creating the client
        # will fail. The lookup, on the other hand, is fit to deal
        # with it.
        client = serv.Serv()
        with mock.patch('serv.utils.IS_DARWIN', return_value=True):
            available_init_systems = client.lookup_init_systems()
            assert available_init_systems == ['launchd']

    def test_bad_niceness_level(self):
        if utils.IS_WIN:
            cmd = find_executable('python') or 'c:\\python27\\python'
        else:
            cmd = find_executable('python2') or '/usr/bin/python2'
        client = serv.Serv()
        with pytest.raises(exceptions.ServError) as ex:
            client.generate(cmd, nice=50)
        assert '`niceness` level must be between' in str(ex)


class TestGenerate:

    service = 'testservice'
    nssm = service + '.bat'
    systemd = service + '.service'
    upstart = service + '.conf'
    sysv = service

    def _get_file_for_system(self, system):
        return os.path.join(
            utils.get_tmp_dir(system, self.service), getattr(self, system))

    def _test_generate(self, system):
        if system == 'nssm':
            self.cmd = find_executable('python') or 'c:\\python27\\python'
        else:
            self.cmd = find_executable('python2') or '/usr/bin/python2'
        self.args = '-m SimpleHTTPServer'
        self.init_script = self._get_file_for_system(system)
        _invoke('generate {0} -n {1} -a "{2}" '
                '-v --overwrite --init-system {3} '
                '--nice=5 --limit-coredump=10 --limit-physical-memory=20 '
                '--var=KEY1=VALUE1'.format(
                    self.cmd, self.service, self.args, system))
        assert self.init_script
        with open(self.init_script) as generated_file:
            self.content = generated_file.read()

    def test_systemd(self):
        try:
            self._test_generate('systemd')
            assert self.cmd + ' ' + self.args in self.content

            assert 'LimitNICE=5' in self.content
            assert 'LimitCORE=10' in self.content
            assert 'LimitRSS=20' in self.content
            env_vars_file = os.path.join(
                utils.get_tmp_dir('systemd', self.service), self.service)
            with open(env_vars_file) as vars_file:
                content = vars_file.read()
            assert 'KEY1=VALUE1' in content
        finally:
            shutil.rmtree(
                os.path.dirname(self.init_script),
                ignore_errors=True)

    def test_upstart(self):
        try:
            self._test_generate('upstart')
            assert self.cmd + ' ' + self.args in self.content

            assert 'nice 5' in self.content
            assert 'limit core 10 10' in self.content
            assert 'limit rss 20 20' in self.content
            assert 'env KEY1=VALUE1' in self.content
        finally:
            shutil.rmtree(
                os.path.dirname(self.init_script),
                ignore_errors=True)

    def test_sysv(self):
        try:
            self._test_generate('sysv')
            assert 'program={0}'.format(self.cmd) in self.content
            assert 'args="{0}"'.format(self.args) in self.content
            assert 'nice -n "$nice"' in self.content
            assert 'ulimit -d 10 -m 20' in self.content
            env_vars_file = os.path.join(
                utils.get_tmp_dir('sysv', self.service),
                self.service + '.defaults')
            with open(env_vars_file) as vars_file:
                content = vars_file.read()
            assert 'nice="5"' in content
        finally:
            shutil.rmtree(
                os.path.dirname(self.init_script),
                ignore_errors=True)

    def test_nssm(self):
        try:
            self._test_generate('nssm')
            assert '"{0}" "{1}" "{2}"'.format(
                self.service, self.cmd, self.args) in self.content
            assert 'KEY1=VALUE1 ^' in self.content
        finally:
            shutil.rmtree(
                os.path.dirname(self.init_script),
                ignore_errors=True)

    @pytest.mark.skipif(utils.IS_WIN, reason='Irrelevant on Windows')
    def test_start_on_unavailable_system(self):
        # This requires a supported init system but that is unavailable
        # which is why nssm is chosen but this is then irrelevant on
        # Windows since it would actually work there.
        try:
            with pytest.raises(exceptions.ServError) as ex:
                client = serv.Serv('nssm')
                client.generate('whatever', name=self.service, start=True)
            assert 'Cannot install nssm service' in str(ex)
        finally:
            shutil.rmtree(
                os.path.dirname(self._get_file_for_system('nssm')),
                ignore_errors=True)

    def test_no_overwrite(self):
        sys = 'systemd'
        cmd = find_executable('python2') or '/usr/bin/python2'
        try:
            command = 'generate {0} -n {1} --init-system {2}'.format(
                cmd, self.service, sys)
            _invoke(command)
            result = _invoke(command)
            assert result.exit_code == 1
            f = self._get_file_for_system(sys)
            assert 'File already exists: {0}'.format(f) in result.output
        finally:
            shutil.rmtree(os.path.dirname(f))

    def test_bad_string_limit_value(self):
        result = _invoke('generate /usr/bin/python2 -n {0} -v --overwrite '
                         '--init-system=systemd --limit-coredump=asd'.format(
                             self.service))
        assert 'All limits must be integers' in result.output

    def test_bad_negative_int_limit_value(self):
        cmd = find_executable('python2') or '/usr/bin/python2'
        result = _invoke('generate {0} -n {1} -v --overwrite '
                         '--init-system=systemd --limit-stack-size=-10'.format(
                             cmd, self.service))
        assert 'All limits must be integers' in result.output

    def test_command_executable_not_found(self):
        service_name = 'testservice'
        from .mock_system import MockSystem, MOCK_INIT_SYSTEM_DIR
        serv.INIT_SYSTEM_MAPPING['mock'] = MockSystem

        executable = 'non_existing_executable'
        service_name = 'testservice'
        client = serv.Serv('mock')
        try:
            with pytest.raises(exceptions.ServError) as ex:
                client.generate(
                    executable,
                    name=service_name,
                    deploy=True)
            assert 'Executable {0} could not be'.format(executable) in str(ex)
        finally:
            shutil.rmtree(MOCK_INIT_SYSTEM_DIR, ignore_errors=True)


class TestDeployMock:
    service_name = 'testservice'
    from . import mock_system
    serv.INIT_SYSTEM_MAPPING['mock'] = mock_system.MockSystem

    def test_flow(self):
        executable = find_executable('python') or '/usr/bin/python2'
        client = serv.Serv('mock')
        try:
            files = client.generate(executable, self.service_name)
            for f in files:
                assert os.path.isfile(f)
            destination_path = os.path.join(
                self.mock_system.MOCK_INIT_SYSTEM_DIR, self.service_name)
            assert not os.path.isfile(destination_path)
            client.generate(executable, self.service_name, deploy=True)
            assert os.path.isfile(destination_path)
            client.generate(
                executable,
                self.service_name,
                overwrite=True,
                deploy=True,
                start=True)
            assert os.path.isfile(destination_path + '.started')

            client.restart(self.service_name)
            assert os.path.isfile(destination_path + '.started')
            client.stop(self.service_name)
            assert not os.path.isfile(destination_path + '.started')
            client.start(self.service_name)
            assert os.path.isfile(destination_path + '.started')
            status = client.status(self.service_name)['services'][0]
            assert status['name'] == self.service_name
            assert status['started']
            assert status['installed']
            client.remove(self.service_name)
            assert not os.path.isfile(destination_path)
        finally:
            shutil.rmtree(
                self.mock_system.MOCK_INIT_SYSTEM_DIR, ignore_errors=True)

# TODO: Test CLI using the mock system flow
