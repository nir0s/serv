from setuptools import setup, find_packages
import os
import codecs

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    # intentionally *not* adding an encoding option to open
    return codecs.open(os.path.join(here, *parts), 'r').read()


def _get_package_data():
    """Iterates over the `init` dir for directories and returns
    all files within them.

    Only files within `binaries` and `templates` will be added.
    """
    from os.path import join as j
    from os import listdir as ld
    x = 'init'
    b = j('serv', x)
    dr = ['binaries', 'templates']
    return [j(x, d, f) for d in ld(b) if d in dr for f in ld(j(b, d))]

setup(
    name='Serv',
    version="0.0.5",
    url='https://github.com/nir0s/serv',
    author='nir0s',
    author_email='nir36g@gmail.com',
    license='LICENSE',
    platforms='All',
    description='Init system abstraction API and CLI.',
    long_description=read('README.rst'),
    packages=find_packages(exclude=[]),
    package_data={'serv': _get_package_data()},
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
