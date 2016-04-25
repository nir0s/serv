SYSTEMD_SVC_PATH = '/lib/systemd/system'
SYSTEMD_ENV_PATH = '/etc/sysconfig'
UPSTART_SVC_PATH = '/etc/init'
SYSV_SVC_PATH = '/etc/init.d'
SYSV_ENV_PATH = '/etc/default'
NSSM_BINARY_PATH = 'c:\\nssm'
NSSM_SVC_PATH = 'c:\\nssm'

TEMPLATES = {
    'systemd': {
        '.service': '/lib/systemd/system',
        '': '/etc/sysconfig'
    },
    'sysv': {
        '': '/etc/init.d',
        '.defaults': '/etc/default'
    },
    'upstart': {
        '.conf': '/etc/init'
    },
    'nssm': {
        '.bat': 'c:\nssm'
    }
}

DIST_TO_INITSYS = {
    'centos': {
        '5': 'sysv',
        '6': 'upstart',
        '7': 'systemd',
    },
    'redhat': {
        '5': 'sysv',
        '6': 'upstart',
        '7': 'systemd',
    },
    'rhel': {
        '5': 'sysv',
        '6': 'upstart',
        '7': 'systemd',
    },
    'debian': {
        '6': 'sysv',
        '7': 'sysv',
        '8': 'systemd',
    },
    'fedora': {
        '18': 'systemd',
        '19': 'systemd',
        '20': 'systemd',
        '21': 'systemd',
        '23': 'systemd',
        '24': 'systemd'
    },
    'opensuse': {
        '12': 'sysv',
        '13': 'systemd',
    },
    'ubuntu': {
        '12': 'upstart',
        '12': 'upstart',
        '13': 'upstart',
        '13': 'upstart',
        '14': 'upstart',
        '15': 'systemd',
        '16': 'systemd'
    },
    'arch': {
        'any': 'systemd',
    }
}
