import os
import sys
import json
import time
import logging

try:
    import distro
except ImportError:
    pass
import click

from .init.sysv import SysV
from .init.nssm import Nssm
from .init.upstart import Upstart
from .init.systemd import SystemD

from . import utils
from . import constants
from .exceptions import ServError


def setup_logger():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger = logging.getLogger(__name__)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


logger = setup_logger()


INIT_SYSTEM_MAPPING = {
    'sysv': SysV,
    'systemd': SystemD,
    'upstart': Upstart,
    'nssm': Nssm
}


class Serv(object):
    def __init__(self,
                 init_system=None,
                 verbose=False):
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)

        if not init_system:
            result = self.lookup_init_systems()
            if not result:
                raise ServError(
                    'No init system detected. Please open an issue at '
                    'https://github.com/nir0s/serv/issues')
            logger.debug('Autodetected init systems: %s', result)
        self.init_system = init_system or result[0]

        # Params to be used when manipulating a service.
        # this is updated with each scenario.
        self.params = dict(init_sys=self.init_system)

        if self.init_system not in INIT_SYSTEM_MAPPING.keys():
            raise ServError(
                'Init system {0} not supported. Please open an issue at '
                'https://github.com/nir0s/serv/issues'.format(
                    self.init_system))

        self.implementation = INIT_SYSTEM_MAPPING[self.init_system]

    def _parse_service_env_vars(self, env_vars):
        """Return a dict based on `key=value` pair strings.
        """
        env = {}
        for var in env_vars:
            # Yeah yeah.. it's less performant.. splitting twice.. who cares.
            k, v = var.split('=')
            env.update({k: v})
        return env

    def _set_service_name_from_command(self, cmd):
        """Set the name of a service according to the command.

        This is only relevant if the name wasn't explicitly provided.
        Note that this is risky as it sets the name according to the
        name of the file the command is using. If two services
        use the same binary, even if their args are different, they
        will be named the same.
        """
        # TODO: Consider assign incremental integers to the name if a service
        # with the same name already exists.
        name = os.path.basename(cmd)
        logger.info(
            'Service name not supplied. Assigning name according to '
            'executable: %s', name)
        return name

    def generate(self,
                 cmd,
                 name='',
                 overwrite=False,
                 deploy=False,
                 start=False,
                 **params):
        """Generate service files and returns a list of the generated files.

        It will generate configuration file(s) for the service and
        deploy them to the tmp dir on your os.

        If `deploy` is True, the service will be configured to run on the
        current machine.
        If `start` is True, the service will be started as well.
        """
        # TODO: parsing env vars and setting the name should probably be under
        # `base.py`.
        name = name or self._set_service_name_from_command(cmd)
        self.params.update(**params)
        self.params.update(dict(
            cmd=cmd,
            name=name,
            env=self._parse_service_env_vars(params.get('var', '')))
        )
        if 'var' in params:
            self.params.pop('var')
        init = self.implementation(logger=logger, **self.params)

        logger.info(
            'Generating %s files for service %s...',
            self.init_system, name)
        files = init.generate(overwrite=overwrite)
        for f in files:
            logger.info('Generated %s', f)

        if deploy or start:
            init.validate_platform()
            logger.info('Deploying %s service %s...', self.init_system, name)
            init.install()

            if start:
                logger.info(
                    'Starting %s service %s...',
                    self.init_system, name)
                init.start()
            logger.info('Service created')
        return files

    def remove(self, name):
        """Remove a service completely.

        It will try to stop the service and then uninstall it.
        The implementation is, of course, system specific.
        For instance, for upstart, it will `stop <name` and then
        delete /etc/init/<name>.conf.
        """
        init = self._get_implementation(name)
        self._assert_service_installed(init, name)
        logger.info('Removing %s service %s...', self.init_system, name)
        init.stop()
        init.uninstall()
        logger.info('Service removed')

    def status(self, name=''):
        """Return a list containing a single service's info if `name`
        is supplied, else returns a list of all services' info.
        """
        logger.warn(
            'Note that `status` is currently not so robust and may break on '
            'different systems')
        init = self._get_implementation(name)
        if name:
            self._assert_service_installed(init, name)
        logger.info('Retrieving status...')
        return init.status(name)

    def stop(self, name):
        """Stop a service
        """
        init = self._get_implementation(name)
        self._assert_service_installed(init, name)
        logger.info('Stopping service: %s...', name)
        init.stop()

    def start(self, name):
        """Start a service
        """
        init = self._get_implementation(name)
        self._assert_service_installed(init, name)
        logger.info('Starting service: %s...', name)
        init.start()

    def restart(self, name):
        """Restart a service
        """
        init = self._get_implementation(name)
        self._assert_service_installed(init, name)
        logger.info('Restarting service: %s...', name)
        init.stop()
        # Here we would use status to verify that the service stopped
        # before restarting. If only status was stable. eh..
        # The arbitrarity of this sleep time is making me sick...
        time.sleep(3)
        init.start()

    def _get_implementation(self, name):
        self.params.update(dict(name=name))
        return self.implementation(logger=logger, **self.params)

    @staticmethod
    def _assert_service_installed(init, name):
        if not init.is_service_exists():
            raise ServError('Service %s does not seem to be installed', name)

    def lookup_init_systems(self):
        """Return the relevant init system and its version.

        This will try to look at the mapping first. If the mapping
        doesn't exist, it will try to identify it automatically.

        Windows lookup is not supported and `nssm` is assumed.
        """
        if utils.IS_WIN:
            logger.debug(
                'Lookup is not supported on Windows. Assuming nssm...')
            return ['nssm']
        if utils.IS_DARWIN:
            logger.debug(
                'Lookup is not supported on OS X, Assuming launchd...')
            return ['launchd']

        logger.debug('Looking up init method...')
        return self._lookup_by_mapping() \
            or self._init_sys_auto_lookup()

    def _is_init_system_installed(self, path):
        return os.path.isdir(path)

    def _init_sys_auto_lookup(self):
        """Return a list of tuples of available init systems on the
        current machine.

        Note that in some situations (Ubuntu 14.04 for instance) more than
        one init system can be found.
        """
        # TODO: Instead, check for executables for systemd and upstart
        # systemctl for systemd and initctl for upstart.
        # An alternative might be to check the second answer here:
        # http://unix.stackexchange.com/questions/196166/how-to-find-out-if-a-system-uses-sysv-upstart-or-systemd-initsystem
        # TODO: Move to each system's implementation
        init_systems = []
        if self._is_init_system_installed('/usr/lib/systemd'):
            init_systems.append('systemd')
        if self._is_init_system_installed('/usr/share/upstart'):
            init_systems.append('upstart')
        if self._is_init_system_installed('/etc/init.d'):
            init_systems.append('sysv')
        return init_systems

    @staticmethod
    def _lookup_by_mapping():
        """Return a the init system based on a constant mapping of
        distribution+version to init system..

        See constants.py for the mapping.
        A failover of the version is proposed for when no version is supplied.
        For instance, Arch Linux's version will most probably be "rolling" at
        any given time, which means that the init system cannot be idenfied
        by the version of the distro.

        On top of trying to identify by the distro's ID, if /etc/os-release
        contains an "ID_LIKE" field, it will be tried. That, again is true
        for Arch where the distro's ID changes (Manjaro, Antergos, etc...)
        But the "ID_LIKE" field is always (?) `arch`.
        """
        like = distro.like().lower()
        distribution_id = distro.id().lower()
        version = distro.major_version()
        if 'arch' in (distribution_id, like):
            version = 'any'
        init_sys = constants.DIST_TO_INITSYS.get(
            distribution_id, constants.DIST_TO_INITSYS.get(like))
        if init_sys:
            system = init_sys.get(version)
            return [system] if system else []


init_system_option = click.option(
    '--init-system',
    required=False,
    type=click.Choice(INIT_SYSTEM_MAPPING.keys()),
    help='Init system to use. (If omitted, will attempt to automatically '
         'identify it.)')
verbosity_option = click.option('-v', '--verbose', default=False, is_flag=True)


@click.group()
def main():
    """Create, remove and manage services on different platforms using a single
    API
    """


@main.command()
@click.argument('COMMAND')
@click.option('-n',
              '--name',
              help='Name of service to create. If omitted, will be deducated '
                   'from the name of the executable')
@click.option('--description',
              default='no description given',
              help='Service\'s description string')
@click.option('-d',
              '--deploy',
              default=False,
              is_flag=True,
              help='Deploy the service on the current machine')
@click.option('-s',
              '--start',
              default=False,
              is_flag=True,
              help='Start the service after deploying it')
@click.option('--overwrite',
              default=False,
              is_flag=True,
              help='Whether to overwrite the service if it already exists')
@click.option('-a',
              '--args',
              help='Arguments to pass to the command')
@click.option('-e',
              '--var',
              multiple=True,
              help='Environment variables to pass to the command. '
                   'Format: var=value. You can do this multiple times')
@click.option('-u',
              '--user',
              default='root',
              help='User to execute `cmd` with. [Default: root]')
@click.option('-g',
              '--group',
              default='root',
              help='Group for `user`. [Default: root]')
@click.option('--chroot',
              default='/',
              help='chroot dir to use. [Default: /]')
@click.option('--chdir',
              default='/',
              help='Directory to change to before executing `cmd`. '
                   '[Default: /]')
@click.option('--nice',
              type=click.IntRange(-20, 19),
              help="process's `niceness` level. [-20 >< 19]")
# TODO: add validation that valid umask.
@click.option('--umask',
              type=int,
              help="process's `niceness` level. [e.g. 755]")
@click.option('--limit-coredump',
              default=None,
              help="process's `limit-coredump` level. "
                   '[`ulimited` || > 0 ]')
@click.option('--limit-cputime',
              default=None,
              help="process's `limit-cputime` level. "
                   '[`ulimited` || > 0 ]')
@click.option('--limit-data',
              default=None,
              help="process's `limit-data` level. "
                   '[`ulimited` || > 0 ]')
@click.option('--limit-file-size',
              default=None,
              help="process's `limit-file-size` level. "
                   '[`ulimited` || > 0 ]')
@click.option('--limit-locked-memory',
              default=None,
              help="process's `limit-locked-memory` level. "
                   '[`ulimited` || > 0 ]')
@click.option('--limit-open-files',
              default=None,
              help="process's `limit-open-files` level. "
                   '[`ulimited` || > 0 ]')
@click.option('--limit-user-processes',
              default=None,
              help="process's `limit-user-processes` level. "
                   '[`ulimited` || > 0 ]')
@click.option('--limit-physical-memory',
              default=None,
              help="process's `limit-physical-memory` level. "
                   '[`ulimited` || > 0 ]')
@click.option('--limit-stack-size',
              default=None,
              help="process's `limit-stack-size` level. "
                   '[`ulimited` || > 0 ]')
@init_system_option
@verbosity_option
def generate(command,
             name,
             init_system,
             overwrite,
             deploy,
             start,
             verbose,
             **params):
    """Create a service.

    `COMMAND` is the path to the executable to run
    """
    # TODO: Add a `prefix` flag which can be used to prefix
    # `COMMAND` with `su -c`, etc..
    try:
        Serv(init_system, verbose=verbose).generate(
            command, name, overwrite, deploy, start, **params)
    except ServError as ex:
        sys.exit(ex)


@main.command()
@click.argument('name')
@init_system_option
@verbosity_option
def remove(name, init_system, verbose):
    """Stop and Removes a service
    """
    try:
        Serv(init_system, verbose=verbose).remove(name)
    except ServError as ex:
        sys.exit(ex)


@main.command()
@click.argument('name', required=False)
@init_system_option
@verbosity_option
def status(name, init_system, verbose):
    """WIP! Try at your own expense
    """
    try:
        status = Serv(init_system, verbose=verbose).status(name)
    except ServError as ex:
        sys.exit(ex)
    click.echo(json.dumps(status, indent=4, sort_keys=True))


@main.command()
@click.argument('name')
@init_system_option
@verbosity_option
def stop(name, init_system, verbose):
    """Stop a service
    """
    try:
        Serv(init_system, verbose=verbose).stop(name)
    except ServError as ex:
        sys.exit(ex)


@main.command()
@click.argument('name')
@init_system_option
@verbosity_option
def start(name, init_system, verbose):
    """Start a service
    """
    try:
        Serv(init_system, verbose=verbose).start(name)
    except ServError as ex:
        sys.exit(ex)


@main.command()
@click.argument('name')
@init_system_option
@verbosity_option
def restart(name, init_system, verbose):
    """Restart a service
    """
    try:
        Serv(init_system, verbose=verbose).restart(name)
    except ServError as ex:
        sys.exit(ex)
