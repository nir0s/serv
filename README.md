Serv
====

[![Build Status](https://travis-ci.org/nir0s/serv.svg?branch=master)](https://travis-ci.org/nir0s/serv)
[![PyPI](http://img.shields.io/pypi/dm/serv.svg)](http://img.shields.io/pypi/dm/serv.svg)
[![PypI](http://img.shields.io/pypi/v/serv.svg)](http://img.shields.io/pypi/v/serv.svg)

Serv creates, removes and manages services on multiple init systems (process managers? service managers? can someone come up with a normal name for this? jeez.)

Serv is a Pythonic spinoff of Jordan Sissel's brilliant [pleaserun](http://github.com/jordansissel/pleaserun).
The question that Serv tries to answer is: "Why the hell do I have to know init systems? I just want this to run forever."

## Features

* Abstracts away the platform (systemd, upstart, etc..) - Serv identifies it by itself.
* Creates daemon configuration on different platforms so that you don't have to.
* Allows to run services after generating the config.
* Allows to stop and remove services.
* Provides both an API and CLI for those purposes.
* Provides an API for retrieving service related information.

NOTE: Serv requires sudo permissions! (you can't write to /etc/init.d, /lib/systemd/system and the others without root can ya?)

### Supported Init Systems

systemd, Upstart and SysV are mostly supported now.

I intend to add:

* runit
* supervisord
* nssm for Windows.
* Whichever other system that's giving you (or me) a headache.

Note: On Linux, Serv uses [ld](http://github.com/nir0s/ld) to identify the distribution.

## Installation

```shell
pip install serv
```

For dev:

```shell
pip install https://github.com/nir0s/serv/archive/master.tar.gz
```

## Usage

### Creating a daemon

```shell
sudo serv generate /usr/bin/python2 --name MySimpleHTTPServer --args '-m SimpleHTTPServer' --var KEY1=VALUE1 --var KEY2=VALUE2 --start -v
```

If name is omitted, the name of the service (and therefore, the names of the files) will be deduced from the executable's name.

### Removing a daemon

```shell
sudo serv remove MySimpleHTTPServer
```

### Retrieving a daemon's status

```shell
sudo serv status MySimpleHTTPServer
```

or for all services

```shell
sudo serv status
```


## Caveats

Init system identification is not robust. It relies on some assumptions (and as we all know, assumption is the mother of all fuckups). Some OS distributions have multiple init systems (Ubuntu 14.04 has Upstart, SysV and half (HALF!?) of systemd).


## Testing

```shell
git clone git@github.com:nir0s/serv.git
cd ld
pip install tox
tox
```

## Contributions..

Pull requests are always welcome to deal with specific distributions or just for general merriment.
