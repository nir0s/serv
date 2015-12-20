from setuptools import setup, find_packages
import os
import codecs

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    # intentionally *not* adding an encoding option to open
    return codecs.open(os.path.join(here, *parts), 'r').read()


setup(
    name='Serv',
    version="0.0.3",
    url='https://github.com/nir0s/serv',
    author='nir0s',
    author_email='nir36g@gmail.com',
    license='LICENSE',
    platforms='All',
    description='Init systems abstraction API and CLI.',
    long_description=read('README.rst'),
    packages=find_packages(exclude=[]),
    package_data={
        'serv': [
            'init/templates/systemd_default.env.j2',
            'init/templates/systemd_default.service.j2',
            'init/templates/upstart_1.5.conf.j2',
            'init/templates/upstart_default.conf.j2',
            'init/templates/sysv_default.j2',
            'init/templates/sysv_default.default.j2',
            'init/templates/sysv_lsb-3.1.j2',
            'init/templates/supervisor_default.conf.j2'
        ]
    },
    entry_points={
        'console_scripts': [
            'serv = serv.serv:main',
        ]
    },
    install_requires=[
        "click==6.2",
        "ld==0.1.2",
        "sh==1.11",
        "jinja2==2.8"
    ],
)
