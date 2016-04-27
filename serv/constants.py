# ["amazon", "2014.09"] => ["upstart", "0.6.5"],
# ["arch", "rolling"] => ["systemd", "default"],
# ["mac_os_x", "10.10"] => ["launchd", "10.9"],
# ["mac_os_x", "10.8"] => ["launchd", "10.9"],
# ["mac_os_x", "10.9"] => ["launchd", "10.9"],

SYSTEMD_SVC_PATH = '/lib/systemd/system'
SYSTEMD_ENV_PATH = '/etc/sysconfig'
UPSTART_SVC_PATH = '/etc/init'
SYSV_SVC_PATH = '/etc/init.d'
SYSV_ENV_PATH = '/etc/default'
NSSM_BINARY_PATH = 'c:\\nssm'
NSSM_SVC_PATH = 'c:\\nssm'

TEMPLATES = {
    'systemd': {
        'default': {
            '.service': '/lib/systemd/system',
            '': '/etc/sysconfig',
        }
    },
    'sysv': {
        'default': {
            '': '/etc/init.d',
            '.defaults': '/etc/default',
        }
    },
    'upstart': {
        'default': {
            '.conf': '/etc/init',
        },
        '1.5': {
            '.conf': '/etc/init',
        }
    },
    'nssm': {
        'default': {
            '.bat': 'c:\nssm',
        }
    }
}

DIST_TO_INITSYS = {
    'centos': {
        '5': ('sysv', 'lsb-3.1'),
        '6': ('upstart', '0.6.5'),
        '7': ('systemd', 'default'),
    },
    'redhat': {
        '5': ('sysv', 'lsb-3.1'),
        '6': ('upstart', '0.6.5'),
        '7': ('systemd', 'default'),
    },
    'rhel': {
        '5': ('sysv', 'lsb-3.1'),
        '6': ('upstart', '0.6.5'),
        '7': ('systemd', 'default'),
    },
    'debian': {
        '6': ('sysv', 'lsb-3.1'),
        '7': ('sysv', 'lsb-3.1'),
        '8': ('systemd', 'default'),
    },
    'fedora': {
        '18': ('systemd', 'default'),
        '19': ('systemd', 'default'),
        '20': ('systemd', 'default'),
        '21': ('systemd', 'default'),
    },
    'opensuse': {
        '12': ('sysv', 'lsb-3.1'),
        '13': ('systemd', 'default'),
    },
    'ubuntu': {
        '12': ('upstart', '1.5'),
        '12': ('upstart', '1.5'),
        '13': ('upstart', '1.5'),
        '13': ('upstart', '1.5'),
        '14': ('upstart', '1.5'),
        '15': ('systemd', 'default'),
        '16': ('systemd', 'default'),
    },
    'arch': {
        'any': ('systemd', 'default'),
    }
}
