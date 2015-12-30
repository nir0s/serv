import os
import re
import logging
import json
import sys

from . import utils
import click

from . import logger
from . import constants as const
from .init.base import Base


lgr = logger.init()


class Serv(object):
    def __init__(self, init_system=None, init_system_version=None,
                 verbose=False):
        if verbose:
            lgr.setLevel(logging.DEBUG)
        else:
            lgr.setLevel(logging.INFO)

        if not init_system or not init_system_version:
            result = self.lookup()
        self.init_sys = init_system or result[0][0]
        self.init_sys_ver = init_system_version or result[0][1]

        if not init_system:
            lgr.debug('Autodetected init system: {0}'.format(
                self.init_sys))
        if not init_system_version:
            lgr.debug('Autodetected init system version: {0}'.format(
                self.init_sys_ver))

        # params to be used when manipulating a service.
        # this is updated in each scenario.
        self.params = dict(
            init_sys=self.init_sys, init_sys_ver=self.init_sys_ver)

        # all implementation objects
        imps = self._find_all_implementations()
        # lowercase names of all implementations (e.g. [sysv, systemd])
        self.implementations = \
            [i.__name__.lower() for i in imps if i.__name__.lower() != 'base']

        if self.init_sys not in self.implementations:
            lgr.error('init system {0} not supported'.format(self.init_sys))
            sys.exit(1)
        # a class object which can be instantiated to control
        # a service.
        # this is instantiated with the relevant parameters (self.params)
        # in each scenario.
        self.implementation = self._get_init_system(imps)

    def _get_init_system(self, init_systems):
        for system in init_systems:
            if system.__name__.lower() == self.init_sys:
                return system

    def _find_all_implementations(self):
        """Returns an init system implementation based on the
        manual mapping or automated lookup.

        All implementations must be loaded within `init/__init__.py`.
        The implementations are retrieved by looking at all subclasses
        of `Base`. A list of all implementations inheriting from Base
        is returned.
        """
        init_systems = []

        def get_implemenetations(inherit_from):
            init_systems.append(inherit_from)
            subclasses = inherit_from.__subclasses__()
            if subclasses:
                for subclass in subclasses:
                    get_implemenetations(subclass)

        lgr.debug('Finding init system implementations...')
        get_implemenetations(Base)
        return init_systems

    def _parse_env_vars(self, env_vars):
        """Returns a dict based on `key=value` pair strings.

        Yeah yeah.. it's less performant.. splitting twice.. who cares.
        """
        env = {}
        for var in env_vars:
            k, v = var.split('=')
            env.update({k: v})
        return env

    def _set_name(self, cmd):
        """Sets the name of a service according to the command.

        This is only relevant if the name wasn't explicitly provided.
        Note that this is risky as it sets the name according to the
        name of the file the command is using. If two services
        use the same binary, even if their args are different, they
        will be named the same.
        """
        name = os.path.basename(cmd)
        lgr.info('Service name not supplied. Assigning '
                 'name according to executable: {0}'.format(name))
        return name

    def generate(self, cmd, name='', overwrite=False, deploy=False,
                 start=False, **params):
        """Generates service files and returns a list of the generated files.

        It will generate configuration file(s) for the service and
        deploy them to the tmp dir on your os.

        If `deploy` is True, the service will be configured to run on the
        current machine.
        If `start` is True, the service will be started as well.
        """
        if start and not deploy:
            lgr.error('Cannot start a service without deploying it.')
            sys.exit(1)

        # TODO: parsing env vars and setting the name should probably be under
        # `base.py`.
        name = name or self._set_name(cmd)
        self.params.update(**params)
        self.params.update(dict(
            cmd=cmd,
            name=name,
            env=self._parse_env_vars(params.get('var', '')))
        )
        self.params.pop('var')
        self._verify_implementation_found()
        self.init = self.implementation(lgr=lgr, **self.params)

        lgr.info('Generating {0} files for service {1}...'.format(
            self.init_sys, name))
        files = self.init.generate(overwrite=overwrite)
        for f in files:
            lgr.info('Generated {0}'.format(f))
        if deploy:
            self.init.validate_platform()
            if not self.init.is_system_exists():
                lgr.error('Cannot install service. {0} is not installed '
                          'on this system.'.format(self.init_sys))
                sys.exit(1)
            lgr.info('Deploying {0} service {1}...'.format(
                self.init_sys, name))
            self.init.install()
            if start:
                lgr.info('Starting {0} service {1}...'.format(
                    self.init_sys, name))
                self.init.start()
            lgr.info('Service created.')
        return files

    def remove(self, name):
        """Removes a service completely.

        It will try to stop the service and then uninstall it.
        The implementation is, of course, system specific.
        For instance, for upstart, it will `stop <name` and then
        delete /etc/init/<name>.conf.
        """
        self.params.update(dict(name=name))
        self._verify_implementation_found()
        init = self.implementation(lgr=lgr, **self.params)
        if not init.is_service_exists():
            lgr.info('Service {0} does not seem to be installed'.format(
                name))
            sys.exit(1)
        lgr.info('Removing {0} service {1}...'.format(self.init_sys, name))
        init.stop()
        init.uninstall()
        lgr.info('Service removed.')

    def status(self, name=''):
        """Returns a list containing a single service's info if `name`
        is supplied, else returns a list of all services' info.
        """
        self.params.update(dict(name=name))
        self._verify_implementation_found()
        init = self.implementation(lgr=lgr, **self.params)

        if name:
            if not init.is_service_exists():
                lgr.info('Service {0} does not seem to be installed'.format(
                    name))
                sys.exit(1)
        lgr.info('Retrieving status...'.format(name))
        return init.status(name)

    def _verify_implementation_found(self):
        if not self.implementation:
            lgr.error('No init system implementation could be found.')
            sys.exit(1)

    def lookup(self):
        """Returns the relevant init system and its version.

        This will try to look at the mapping first. If the mapping
        doesn't exist, it will try to identify it automatically.

        Windows lookup is not supported and `nssm` is assumed.
        """
        if utils.IS_WIN:
            lgr.info('Lookup is not supported on Windows. Assuming nssm.')
            return [('nssm', 'default')]
        if utils.IS_DARWIN:
            lgr.info('Lookup is not supported on OS X, Assuming Launchd.')
            return [('launchd', 'default')]
        lgr.debug('Looking up init method...')
        return self._lookup_by_mapping() \
            or self._auto_lookup()

    @staticmethod
    def _get_upstart_version():
        """Returns the upstart version if it exists.
        """
        import sh
        try:
            output = sh.initctl.version()
        except:
            return
        version = re.search(r'(\d+((.\d+)+)+?)', str(output))
        if version:
            return str(version.group())
        return None

    @staticmethod
    def _get_systemctl_version():
        """Returns the systemd version if it exists.
        """
        import sh
        try:
            output = sh.systemctl('--version').split('\n')[0]
        except:
            return
        version = re.search(r'(\d+)', str(output))
        if version:
            return str(version.group())
        return None

    def _auto_lookup(self):
        """Returns a list of tuples of available init systems on the
        current machine.

        Note that in some situations (Ubuntu 14.04 for instance) more than
        one init system can be found.
        """
        init_systems = []
        if os.path.isdir('/usr/lib/systemd'):
            version = self._get_systemctl_version()
            if version:
                init_systems.append('systemd', version or 'default')
        if os.path.isdir('/usr/share/upstart'):
            version = self._get_upstart_version()
            if version:
                init_systems.append('upstart', version or 'default')
        if os.path.isdir('/etc/init.d'):
            init_systems.append('sysv', 'lsb-3.1')
        return init_systems

    @staticmethod
    def _lookup_by_mapping():
        """Returns a tuple containing the init system's type and version based
        on a constant mapping of distribution+version to init system..

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
        import ld
        like = ld.like().lower()
        distro = ld.id().lower()
        version = ld.major_version()
        # init (upstart 1.12.1)
        if distro in ('arch'):
            version = 'any'
        elif like in ('arch'):
            version = 'any'
        d = const.DIST_TO_INITSYS.get(distro, const.DIST_TO_INITSYS.get(like))
        if d:
            return [d.get(version)] or []


@click.group()
def main():
    pass


@click.command()
@click.argument('cmd', required=True)
@click.option('-n', '--name',
              help='Name of service to create. If omitted, will be deducated '
              'from the name of the executable.')
@click.option('--description', default='no description given',
              help='Service\'s description string.')
@click.option('-d', '--deploy', default=False, is_flag=True,
              help='Deploy the service on the current machine.')
@click.option('-s', '--start', default=False, is_flag=True,
              help='Start the service after deploying it.')
@click.option('--init-system', required=False,
              type=click.Choice(Serv().implementations),
              help='Init system to use. (If omitted, will attempt to '
              'automatically identify it.)')
@click.option('--init-system-version', required=False, default='default',
              type=click.Choice(['lsb-3.1', '1.5', 'default']),
              help='Init system version to use. (If omitted, will attempt to '
              'automatically identify it.)')
@click.option('--overwrite', default=False, is_flag=True,
              help='Whether to overwrite the service if it already exists.')
@click.option('-a', '--args', required=False,
              help='Arguments to pass to the command.')
@click.option('-e', '--var', required=False, multiple=True,
              help='Environment variables to pass to the command. '
                   'Format: var=value. You can do this multiple times.')
@click.option('-u', '--user', required=False, default='root',
              help='User to execute `cmd` with. [Default: root]')
@click.option('-g', '--group', required=False, default='root',
              help='Group for `user`. [Default: root].')
@click.option('--chroot', required=False, default='/',
              help='chroot dir to use. [Default: /]')
@click.option('--chdir', required=False, default='/',
              help='Directory to change to before executing `cmd`. '
              '[Default: /]')
@click.option('--nice', required=False, type=click.IntRange(-20, 19),
              help='process\'s `niceness` level. [-20 >< 19]')
# TODO: add validation that valid umask.
@click.option('--umask', required=False, type=int,
              help='process\'s `niceness` level. [e.g. 755]')
@click.option('--limit-coredump', required=False, default=None,
              help='process\'s `limit-coredump` level. '
              '[`ulimited` || > 0 ]')
@click.option('--limit-cputime', required=False, default=None,
              help='process\'s `limit-cputime` level. '
              '[`ulimited` || > 0 ]')
@click.option('--limit-data', required=False, default=None,
              help='process\'s `limit-data` level. '
              '[`ulimited` || > 0 ]')
@click.option('--limit-file_size', required=False, default=None,
              help='process\'s `limit-file-size` level. '
              '[`ulimited` || > 0 ]')
@click.option('--limit-locked-memory', required=False, default=None,
              help='process\'s `limit-locked-memory` level. '
              '[`ulimited` || > 0 ]')
@click.option('--limit-open-files', required=False, default=None,
              help='process\'s `limit-open-files` level. '
              '[`ulimited` || > 0 ]')
@click.option('--limit-user-processes', required=False, default=None,
              help='process\'s `limit-user-processes` level. '
              '[`ulimited` || > 0 ]')
@click.option('--limit-physical-memory', required=False, default=None,
              help='process\'s `limit-physical-memory` level. '
              '[`ulimited` || > 0 ]')
@click.option('--limit-stack-size', required=False, default=None,
              help='process\'s `limit-stack-size` level. '
              '[`ulimited` || > 0 ]')
@click.option('-v', '--verbose', default=False, is_flag=True)
def generate(cmd, name, init_system, init_system_version, overwrite,
             deploy, start, verbose, **params):
    """Creates (and maybe runs) a service.
    """
    logger.configure()
    Serv(init_system, init_system_version, verbose).generate(
        cmd, name, overwrite, deploy, start, **params)


@click.command()
@click.argument('name')
@click.option('--init-system', required=False,
              type=click.Choice(Serv().implementations),
              help='Init system to use.')
@click.option('-v', '--verbose', default=False, is_flag=True)
def remove(name, init_system, verbose):
    """Stops and Removes a service
    """
    logger.configure()
    Serv(init_system, verbose).remove(name)


@click.command()
@click.argument('name', required=False)
@click.option('--init-system', required=False,
              type=click.Choice(Serv().implementations),
              help='Init system to use.')
@click.option('-v', '--verbose', default=False, is_flag=True)
def status(name, init_system, verbose):
    """Retrieves a service's status.

    If `init-system` is omitted,
    a service named `name` will be looked for under the
    automatically identified init system.

    If `name` is omitted, a status of all services will be
    retrieved.
    """
    logger.configure()
    status = Serv(init_system, verbose).status(name)
    print(json.dumps(status, indent=4, sort_keys=True))


main.add_command(generate)
main.add_command(remove)
main.add_command(status)
