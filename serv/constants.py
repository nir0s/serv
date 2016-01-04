# ["amazon", "2014.09"] => ["upstart", "0.6.5"],
# ["arch", "rolling"] => ["systemd", "default"],
# ["mac_os_x", "10.10"] => ["launchd", "10.9"],
# ["mac_os_x", "10.8"] => ["launchd", "10.9"],
# ["mac_os_x", "10.9"] => ["launchd", "10.9"],

SYSTEMD_SVC_PATH = '/lib/systemd/system'
SYSTEMD_ENV_PATH = '/etc/sysconfig'
UPSTART_SCRIPT_PATH = '/etc/init'
SYSV_SCRIPT_PATH = '/etc/init.d'
SYSV_ENV_PATH = '/etc/default'
RUNIT_SCRIPT_PATH = 'etc/service/'
NSSM_BINARY_LOCATION = 'c:\\nssm'
NSSM_SCRIPT_PATH = 'c:\\nssm'

TEMPLATES = {
    'systemd': {
        'default': {
            'systemd_default.service.j2': '/lib/systemd/system',
            'systemd_default.env.j2': '/etc/sysconfig'
        }
    },
    'sysv': {
        'default': {
            'sysv_default.default.j2': '/etc/default',
            'sysv_default.j2': '/etc/init.d'
        }
    },
    'upstart': {
        'default': {
            'upstart_default.conf.j2': '/etc/init'
        },
        '1.5': {
            'upstart_1.5.conf.j2': '/etc/init'
        }
    },
    'nssm': {
        'default': {
            'nssm_default.conf.j2': 'c:\\nssm'
        }
    }
}

DIST_TO_INITSYS = {
    'centos': {
        '5': ('sysv', 'lsb-3.1'),
        '6': ('upstart', '0.6.5'),
        '7': ('systemd', 'default')
    },
    'redhat': {
        '5': ('sysv', 'lsb-3.1'),
        '6': ('upstart', '0.6.5'),
        '7': ('systemd', 'default')
    },
    'rhel': {
        '5': ('sysv', 'lsb-3.1'),
        '6': ('upstart', '0.6.5'),
        '7': ('systemd', 'default')
    },
    'debian': {
        '6': ('sysv', 'lsb-3.1'),
        '7': ('sysv', 'lsb-3.1'),
        '8': ('systemd', 'default')
    },
    'fedora': {
        '18': ('systemd', 'default'),
        '19': ('systemd', 'default'),
        '20': ('systemd', 'default'),
        '21': ('systemd', 'default')
    },
    'opensuse': {
        '12': ('sysv', 'lsb-3.1'),
        '13': ('systemd', 'default')
    },
    'ubuntu': {
        '12': ('upstart', '1.5'),
        '12': ('upstart', '1.5'),
        '13': ('upstart', '1.5'),
        '13': ('upstart', '1.5'),
        '14': ('upstart', '1.5'),
        '15': ('systemd', 'default')
    },
    'arch': {
        'any': ('systemd', 'default')
    }
}
