import os
import re
import sys

from serv import utils
from serv.init.base import Base
from serv import constants as const

if not utils.IS_WIN:
    import sh


class SystemD(Base):
    def __init__(self, lgr=None, **params):
        """Sets the default parameters.

        We're supering this as `Base` is setting up some basic
        globally required parameters. It's a must.

        We check for `self.name` before we set the destination
        paths for the service files as sometimes `self.name`
        is not provided (for instance, when retrieving status
        for all services under the init system.)

        `self.name` is set in `base.py`
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

        Note that the parameters required to generate the file are
        propagated automatically which is why we don't pass them explicitly
        to the generating function.

        `self.template_prefix` and `self.generate_into_prefix` are set in
         `base.py`

        `self.files` is an automatically generated list of the files that
        were generated during the process. It should be returned so that
        the generated files could be printed out for the user.
        """
        super(SystemD, self).generate(overwrite=overwrite)
        self._validate_init_system_specific_params()

        svc_file_template = self.template_prefix + '.service'
        env_file_template = self.template_prefix
        self.svc_file_path = self.generate_into_prefix + '.service'
        self.env_file_path = self.generate_into_prefix

        self.generate_file_from_template(svc_file_template, self.svc_file_path)
        self.generate_file_from_template(env_file_template, self.env_file_path)
        return self.files

    def install(self):
        """Installs the service on the local machine

        This is where we deploy the service files to their relevant
        locations and perform any other required actions to configure
        the service and make it ready to be `start`ed.
        """
        super(SystemD, self).install()

        self.deploy_service_file(self.svc_file_path, self.svc_file_dest)
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
        failures. As such, idempotence should be considered.
        """
        sh.systemctl.disable(self.name)
        sh.systemctl('daemon-reload')
        if os.path.isfile(self.svc_file_dest):
            os.remove(self.svc_file_dest)
        if os.path.isfile(self.env_file_dest):
            os.remove(self.env_file_dest)

    def status(self, name=''):
        """Returns a list of the statuses of the `name` service, or
        if name is omitted, a list of the status of all services for this
        specific init system.

        There should be a standardization around the status fields.
        There currently isn't.

        `self.services` is set in `base.py`
        """
        super(SystemD, self).status(name=name)

        svc_list = sh.systemctl('--no-legend', '--no-pager', t='service')
        svcs_info = [self._parse_service_info(svc) for svc in svc_list]
        if name:
            names = (name, name + '.service')
            # return list of one item for specific service
            svcs_info = [s for s in svcs_info if s['name'] in names]
        self.services['services'] = svcs_info
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

    @staticmethod
    def is_system_exists():
        """Returns True if the init system exists and False if not.
        """
        return is_system_exists()

    @staticmethod
    def get_system_version():
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

    def validate_platform(self):
        if utils.IS_WIN or utils.IS_DARWIN:
            self.lgr.error(
                'Cannot install SysVinit service on non-Linux systems.')
            sys.exit()


def is_system_exists():
    try:
        sh.systemctl('--version')
        return True
    except:
        return False
