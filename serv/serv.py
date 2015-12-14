import os
import re
import logging
import json

import sh
import ld
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

    @staticmethod
    def _find_init_systems(init_system):
        init_systems = []

        def get_impl(impl):
            init_systems.append(impl)
            subclasses = impl.__subclasses__()
            if subclasses:
                for subclass in subclasses:
                    get_impl(subclass)

        lgr.debug('Finding init implementations...')
        get_impl(Base)
        for system in init_systems:
            if system.__name__.lower() == init_system:
                return system
        return None

    def _parse_env_vars(self, env_vars):
        env = {}
        for var in env_vars:
            key, value = var.split('=')
            env.update(dict(key=value))
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
        lgr.info('Service name not supplied, automatically assigning '
                 'name according to executable: {0}'.format(name))
        return name

    def create(self, cmd, name='', args='',
               description='no description given',
               user='root', group='root', env=None, overwrite=False,
               start=True):
        """Creates a service and returns the files generated to support it.

        It will generate configuration file(s) for the service and
        deploy them.
        If `start` is True, it will also start the service.
        """
        params = dict(
            init_sys=self.init_sys,
            init_sys_ver=self.init_sys_ver,
            cmd=cmd,
            name=name or self._set_name(cmd),
            args=args,
            description=description,
            user=user,
            group=group,
            env=self._parse_env_vars(env)
        )

        lgr.info('Creating {0} Service: {1}...'.format(
            self.init_sys, name))
        init_system = self._find_init_systems(self.init_sys)
        s = init_system(lgr=lgr, **params)
        files = s.generate(overwrite=overwrite)
        s.install()
        if start:
            lgr.info('Starting Service: {0}'.format(name))
            s.start()
        lgr.info('Service created.')
        return files

    def remove(self, name):
        """Removes a service completely.

        It will try to stop the service and then uninstall it.
        The implementation is, of course, system specific.
        For instance, for upstart, it will `stop <name` and then
        delete /etc/init/<name>.conf.
        """
        params = dict(
            init_sys=self.init_sys,
            init_sys_ver=self.init_sys_ver,
            name=name
        )

        lgr.info('Removing Service: {0}...'.format(name))
        init_system = self._find_init_systems(self.init_sys)
        s = init_system(lgr=lgr, **params)
        s.stop()
        s.uninstall()
        lgr.info('Service removed.')

    def status(self, name=''):
        """Returns a list containing a single service's info if `name`
        is supplied, else returns a list of all services' info.
        """
        params = dict(
            init_sys=self.init_sys,
            init_sys_ver=self.init_sys_ver,
            name=name
        )
        lgr.info('Retrieving Status...'.format(name))
        init_system = self._find_init_systems(self.init_sys)
        s = init_system(lgr=lgr, **params)
        return s.status(name)

    def lookup(self):
        """Returns the relevant init system and its version.

        This will try to look at the mapping first. If the mapping
        doesn't exist, it will try to identify it automatically.
        """
        lgr.debug('Looking up init method...')
        return self._lookup_by_mapping() \
            or self._auto_lookup()

    @staticmethod
    def _get_upstart_version():
        """Returns the upstart version if it exists.
        """
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
        try:
            output = sh.systemctl('--version').split('\n')[0]
        except:
            return
        version = re.search(r'(\d+)', str(output))
        if version:
            return str(version.group())
        return None

    def _auto_lookup(self):
        """Returns a tuple containing the init system's type and version
        based on some systematic assumptions.

        Note that in some situations (Ubuntu 14.04 for instance) more than
        one init system can be found. In that case, we'll try to return
        the most relevant one:

        systemd first, upstart second, sysv third.
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
@click.option('-c', '--cmd', required=True,
              help='Absolute or in $PATH command to run.')
@click.option('--init-system', required=False,
              type=click.Choice(['upstart', 'systemd']),
              help='Init system to use.')
@click.option('--init-system-version', required=False, default='default',
              type=click.Choice(['lsb-3.1', '1.5', 'default']),
              help='Init system version to use.')
@click.option('-a', '--args', required=False,
              help='Arguments to pass to the command.')
@click.option('-e', '--var', required=False, multiple=True,
              help='Environment variables to pass to the command. '
                   'Format: var=value. You can do this multiple times.')
@click.option('--overwrite', default=False, is_flag=True,
              help='Whether to overwrite the service if it already exists.')
@click.option('-s', '--start', default=False, is_flag=True,
              help='Start the service after creating it.')
@click.option('-v', '--verbose', default=False, is_flag=True)
def create(cmd, init_system, init_system_version, args, var, overwrite, start,
           verbose):
    """Creates (and maybe runs) a service.
    """
    logger.configure()
    Serv(init_system, init_system_version, verbose).create(
        cmd=cmd, args=args, env=var, overwrite=overwrite, start=start)


@click.command()
@click.option('-n', '--name',
              help='Name of service to remove.')
@click.option('--init-system', required=False,
              type=click.Choice(['upstart', 'systemd']),
              help='Init system to use.')
@click.option('-v', '--verbose', default=False, is_flag=True)
def remove(name, init_system, verbose):
    """Stops and Removes a service
    """
    logger.configure()
    Serv(init_system, verbose).remove(name)


@click.command()
@click.option('-n', '--name', required=False,
              help='Name of service to get status for. If omitted, will '
                   'returns the status for all services.')
@click.option('--init-system', required=False,
              type=click.Choice(['upstart', 'systemd']),
              help='Init system to use.')
@click.option('-v', '--verbose', default=False, is_flag=True)
def status(name, init_system, verbose):
    """Creates a service
    """
    logger.configure()
    status = Serv(init_system, verbose).status(name)
    print(json.dumps(status, indent=4, sort_keys=True))


main.add_command(create)
main.add_command(remove)
main.add_command(status)
