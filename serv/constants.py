# ["amazon", "2014.09"] => ["upstart", "0.6.5"],
# ["arch", "rolling"] => ["systemd", "default"],
# ["mac_os_x", "10.10"] => ["launchd", "10.9"],
# ["mac_os_x", "10.8"] => ["launchd", "10.9"],
# ["mac_os_x", "10.9"] => ["launchd", "10.9"],

SYSTEMD_SVC_PATH = '/lib/systemd/system'
SYSTEMD_ENV_PATH = '/etc/sysconfig'
UPSTART_SCRIPT_PATH = '/etc/init'
SYSV_SCRIPT_PATH = '/etc/init.d'

DIST_TO_INITSYS = {
    'centos': {
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
        '14': ('upstart', '1.5')
    },
    'arch': {
        'any': ('systemd', 'default')
    }
}
