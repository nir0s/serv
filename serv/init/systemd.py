import os
import sys
import re

import sh

from serv.init.base import Base
from serv import constants as const


class SystemD(Base):
    def __init__(self, lgr=None, **params):
        """Sets the default parameters.

        We're supering this as `Base` is setting up some basic
        globallly required parameters. It's a must.

        We check for `self.name` before we set the destination
        paths for the service files as sometimes `self.name`
        is not provided (for instance, when retrieving status
        for all services under the init system.)
        """
        super(SystemD, self).__init__(lgr=lgr, **params)
        if self.name:
            self.svc_file_dest = os.path.join(
                const.SYSTEMD_SVC_PATH, self.name + '.service')
            self.env_file_dest = os.path.join(
                const.SYSTEMD_ENV_PATH, self.name)

    def generate(self, overwrite=False):
        """Generates service files and returns a list of them.

        Note that env var names will be capitalized using a Jinja filter.
        This is template dependent.
        Even though a param might be named `key` and have value `value`,
        it will be rendered as `KEY=value`.

        We retrieve the names of the template files and see the paths
        where the generated files will be deployed. These are files
        a user can just take and use.
        If the service is also installed, those files will be moved
        to the relevant location on the system.
        """
        super(SystemD, self).generate(overwrite=overwrite)
        self._validate_init_system_specific_params()

        # TODO: these should be standardized across all implementations.
        svc_file_tmplt = '{0}_{1}.service.j2'.format(
            self.init_sys, self.init_sys_ver)
        env_file_tmplt = '{0}_{1}.env.j2'.format(
            self.init_sys, self.init_sys_ver)

        self.svc_file_path = os.path.join(self.tmp, self.name + '.service')
        self.env_file_path = os.path.join(self.tmp, self.name)

        files = [self.svc_file_path]

        self.generate_file_from_template(svc_file_tmplt, self.svc_file_path)
        if self.params.get('env'):
            self.generate_file_from_template(
                env_file_tmplt, self.env_file_path)
            files.append(self.env_file_path)

        return files

    def install(self):
        """Installs the service on the local machine

        This is where we deploy the service files to their relevant
        locations and perform any other required actions to configure
        the service and make it ready to be `start`ed.
        """
        super(SystemD, self).install()
        self.deploy_service_file(self.svc_file_path, self.svc_file_dest)
        if self.params.get('env'):
            self.deploy_service_file(self.env_file_path, self.env_file_dest)

        sh.systemctl.enable(self.name)
        sh.systemctl('daemon-reload')

    def start(self):
        """Starts the service.
        """
        sh.systemctl.start(self.name)

    def stop(self):
        """Stops the service.
        """
        try:
            sh.systemctl.stop(self.name)
        except sh.ErrorReturnCode_5:
            self.lgr.debug('Service not running.')

    # TODO: this should be a decorator under base.py to allow
    # cleanup on failed creation.
    def uninstall(self):
        """Uninstalls the service.

        This is supposed to perform any cleanup operations required to
        remove the service. Files, links, whatever else should be removed.
        This method should also run when implementing cleanup in case of
        failures.
        """
        sh.systemctl.disable(self.name)
        sh.systemctl('daemon-reload')
        if os.path.isfile(self.svc_file_dest):
            os.remove(self.svc_file_dest)
        if os.path.isfile(self.env_file_dest):
            os.remove(self.env_file_dest)

    def status(self, name=''):
        """Returns a list of the status(es) of the `name` service, or
        if name is omitted, a list of the status of all services for this
        specific init system.

        There should be a standardization around the status fields.
        There currently isn't.
        """
        super(SystemD, self).status(name=name)
        svc_list = sh.systemctl('--no-legend', '--no-pager', t='service')
        svcs_info = [self._parse_service_info(svc) for svc in svc_list]
        if name:
            names = (name, name + '.service')
            # return list of one item for specific service
            svcs_info = [s for s in svcs_info if s['name'] in names]
        self.services.update({'services': svcs_info})
        return self.services

    @staticmethod
    def _parse_service_info(svc):
        svc_info = svc.split()
        return dict(
            name=svc_info[0],
            load=svc_info[1],
            active=svc_info[2],
            sub=svc_info[3],
            description=svc_info[4]
        )

    def is_system_exists(self):
        """Returns True if the init system exists and False if not.
        """
        try:
            sh.systemctl('--version')
            return True
        except:
            return False

    def get_system_version(self):
        """Returns the init system's version if it exists.
        """
        try:
            output = sh.systemctl('--version').split('\n')[0]
        except:
            return
        version = re.search(r'(\d+)', str(output))
        if version:
            return str(version.group())
        return ''

    def is_service_exists(self):
        return os.path.isfile(self.svc_file_dest)

    def _validate_init_system_specific_params(self):
        if not self.cmd.startswith('/'):
            self.lgr.error('Systemd requires the full path to the executable. '
                           'Instead, you provided: {0}'.format(self.cmd))
            sys.exit()
