from setuptools import setup
import os
import codecs

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    # intentionally *not* adding an encoding option to open
    return codecs.open(os.path.join(here, *parts), 'r').read()


setup(
    name='Serv',
    version="0.0.1",
    url='https://github.com/nir0s/serv',
    author='nir0s',
    author_email='nir36g@gmail.com',
    license='LICENSE',
    platforms='All',
    description='Process Management Identifier and script generator',
    long_description=read('README.rst'),
    packages=[
        'serv',
        'serv.init'
    ],
    package_data={
        'serv': [
            'init/templates/systemd_default.env.j2',
            'init/templates/systemd_default.service.j2',
            'init/templates/upstart_1.5.conf.j2',
            'init/templates/upstart_default.conf.j2'
        ]
    },
    entry_points={
        'console_scripts': [
            'serv = serv.serv:main',
        ]
    },
    install_requires=[
        "click==6.2",
        "ld",
        "sh==1.11",
        "jinja2==2.8"
    ],
)
