Serv
====

[![Build Status](https://travis-ci.org/nir0s/serv.svg?branch=master)](https://travis-ci.org/nir0s/serv)
[![PyPI](http://img.shields.io/pypi/dm/serv.svg)](http://img.shields.io/pypi/dm/serv.svg)
[![PypI](http://img.shields.io/pypi/v/serv.svg)](http://img.shields.io/pypi/v/serv.svg)

Serv creates, removes and manages services on multiple init systems (process managers? service managers? can someone come up with a normal name for this? jeez.)

Serv is a Pythonic spinoff of Jordan Sissel's brilliant [pleaserun](http://github.com/jordansissel/pleaserun).
The question that Serv tries to answer is: "Why the hell do I have to know init systems? I just want this to run forever."

## Features

* Abstracts away the platform (systemd, upstart, etc..) - Serv identifies it by itself thought it can be explicitly provided.
* Creates service configuration files on different platforms so that you don't have to.
* Allows to deploy services after generating the config on the local machine.
* Allows to stop and remove services.
* Provides both an API and CLI for those purposes.
* Provides an API for retrieving service related information.

NOTE: Serv requires sudo permissions! (you can't write to /etc/init.d, /lib/systemd/system and the others without root can ya?)

### Supported Init Systems

[systemd](http://www.freedesktop.org/wiki/Software/systemd/), [Upstart](http://upstart.ubuntu.com/) and [SysV](https://wiki.archlinux.org/index.php/SysVinit) are mostly supported now though SysV doesn't yet support retrieving a service's `status`.
[nssm](https://nssm.cc/) (Non-Sucking Service Manager for Windows) is currently being worked on.

I intend to add:

* runit
* supervisord
* Whichever other system that's giving you (or me) a headache.

Note: On Linux, Serv uses [ld](http://github.com/nir0s/ld) to identify the distribution.

## Compatibility

Currently, tested on Python 2.6.x and 2.7.x
Will be adding Python 3.x support soon enough.

## Installation

```shell
sudo pip install serv
```

For dev:

```shell
sudo pip install https://github.com/nir0s/serv/archive/master.tar.gz
```

## Usage

Before using, please read the caveats section!

### Creating a service

```shell
$ sudo serv generate /usr/bin/python2 --name MySimpleHTTPServer --args '-m SimpleHTTPServer' --var KEY1=VALUE1 --var KEY2=VALUE2 --deploy --start
...

INFO - Generating files for systemd...
INFO - Generated /tmp/SimpleHTTPServer.service
INFO - Generated /tmp/SimpleHTTPServer
INFO - Deploying systemd service SimpleHTTPServer...
INFO - Deploying /tmp/SimpleHTTPServer.service to /lib/systemd/system/SimpleHTTPServer.service...
INFO - Deploying /tmp/SimpleHTTPServer to /etc/sysconfig/SimpleHTTPServer...
INFO - Starting systemd service SimpleHTTPServer...
INFO - Service created.


...

$ ss -lntp | grep 8000
LISTEN     0      5            *:8000                     *:*

```

If name is omitted, the name of the service (and therefore, the names of the files) will be deduced from the executable's name.

### Retrieving a service's status

```shell
$ sudo serv status MySimpleHTTPServer
...

{
    "init_system": "systemd",
    "init_system_version": "default",
    "services": [
        {
            "active": "active",
            "description": "no",
            "load": "loaded",
            "name": "MySimpleHTTPServer.service",
            "sub": "running"
        }
    ]
}

...
```

or for all services of the same init system

```shell
$ sudo serv status
...
```

### Removing a service

```shell
$ sudo serv remove MySimpleHTTPServer
...

INFO - Removing Service: SimpleHTTPServer...
INFO - Service removed.
...

$ ss -lntp | grep 8000
```


## Python API

```python
raise NotImplementedError()
```

Kidding.. it's there, it's easy and it and requires documentation.

## How does it work

Serv, unless explicitly specified by the user, looks up the the platform you're running on (Namely, linux distro and release) and deduces which init system is running on it by checking a static mapping table or an auto-lookup mechanism.

Once an init-system matching an existing implementation (i.e supported by Serv) is found, Serv renders template files based on a set of parameters; (optionally) deploys them to the relevant directories and (optionally) starts the service.

Since Serv is aware of the init system being used, it also knows which files it needs to deploy and to where and which commands it needs to run.

## Caveats and limitations

* Init system identification is not robust. It relies on some assumptions (and as we all know, assumption is the mother of all fuckups). Some OS distributions have multiple init systems (Ubuntu 14.04 has Upstart, SysV and half (HALF!?) of systemd).
* Stupidly enough, I have yet to standardize the status JSON returned and it is different for each init system.
* Currently if anything fails during service creation, cleanup is not performed. This will be added in future versions.
* Currently, all errors exit on the same error level. This will be changed soon.

### Missing directories

In some situations, directories related to the specific init system do not exist and should be created. For instance, even if systemd (`systemctl`) is available, `/etc/sysconfig` does not exist. IT IS UP TO THE USER to create those directories if they don't exist as Serv should not change the system on that level. The exception to the rule is with `nssm`, which will create the required dir (`c:\nssm`) for it to operate.

Required dirs are:

#### Systemd

* `/lib/systemd/system`
* `/etc/sysconfig` (required only if environment variables are provided.)

#### SysV

* `/etc/init.d`
* `/etc/default`

#### Upstart

* `/etc/init`

## Testing

```shell
git clone git@github.com:nir0s/serv.git
cd ld
pip install tox
tox
```

## Contributions..

Pull requests are always welcome to deal with specific distributions or just for general merriment.

### Adding support for additional init-systems.

* Under serv/init, add a file named <init_system_name>.py (e.g. runit.py).
* Implement a class named <init_system_name> (e.g. Runit). See [systemd](https://github.com/nir0s/serv/blob/master/serv/init/systemd.py) as a reference implementation.
* Pass the `Base` class which contains some basic parameter declarations and provides a method for generating files from templates to your class (e.g. `from serv.init.base import Base`).
* Add the relevant template files to serv/init/templates. The file names should be formatted as: `<init_system_name>_<init_system_version>.*.j2` (e.g. runit_default.j2).
* In serv/init/__init__.py, import the class you implemented (e.g. `from serv.init.runit import Runit`).
