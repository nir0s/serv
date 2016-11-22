import os
import codecs
from setuptools import setup, find_packages


def read(*parts):
    here = os.path.abspath(os.path.dirname(__file__))
    # intentionally *not* adding an encoding option to open
    return codecs.open(os.path.join(here, *parts), 'r').read()


def _get_package_data():
    """Iterate over the `init` dir for directories and returns
    all files within them.

    Only files within `binaries` and `templates` will be added.
    """
    from os import listdir as ls
    from os.path import join as jn

    x = 'init'
    b = jn('serv', x)
    dr = ['binaries', 'templates']
    return [jn(x, d, f) for d in ls(b) if d in dr for f in ls(jn(b, d))]


IS_WIN = (os.name == 'nt')
install_requires = [
    "click==6.6",
    "jinja2==2.8"
]
if not IS_WIN:
    non_win_requirements = [
        "sh==1.11",
        "distro==1.0.1",
    ]
    install_requires.extend(non_win_requirements)

setup(
    name='Serv',
    version="0.3.0",
    url='https://github.com/nir0s/serv',
    author='nir0s',
    author_email='nir36g@gmail.com',
    license='LICENSE',
    platforms='All',
    description='Init system abstraction API and CLI',
    long_description=read('README.rst'),
    packages=find_packages(exclude=[]),
    package_data={'serv': _get_package_data()},
    entry_points={
        'console_scripts': [
            'serv = serv.serv:main',
        ]
    },
    install_requires=install_requires,
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Natural Language :: English',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
