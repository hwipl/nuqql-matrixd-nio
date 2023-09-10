# nuqql-matrixd-nio

nuqql-matrixd-nio is a network daemon that implements the nuqql interface and
uses [matrix-nio](https://github.com/poljar/matrix-nio) to connect to Matrix
chat networks. It can be used as a backend for
[nuqql](https://github.com/hwipl/nuqql) or as a standalone chat client daemon.

nuqql-matrixd-nio's dependencies are:
* [nuqql-based](https://github.com/hwipl/nuqql-based)
* [matrix-nio](https://github.com/poljar/matrix-nio) with enabled end-to-end
  encryption which needs [libolm](https://gitlab.matrix.org/matrix-org/olm)
  (version 3.x)
* [daemon](https://pypi.org/project/python-daemon/) (optional)


## Quick Start

Make sure you have libolm installed.

You can install nuqql-matrixd-nio and its other dependencies, for example, with
pip for your user only with the following command:

```console
$ pip install --user nuqql-matrixd-nio
```

After the installation, you can run nuqql-matrixd-nio by running the
`nuqql-matrixd-nio` command:

```console
$ nuqql-matrixd-nio
```

By default, it listens on TCP port 32000 on your local host. So, you can
connect with, e.g., telnet to it with the following command:

```console
$ telnet localhost 32000
```

In the telnet session you can:
* add Matrix accounts with: `account add matrix <account> <password>`.
  * Note: the format of `<account>` is `<username>@<homeserver>`, e.g.,
    `dummy_user@matrix.org`.
* retrieve the list of accounts and their numbers/IDs with `account list`.
* retrieve your buddy/room list with `account <id> buddies` or `account <id>
  chat list`
* send a message to a room with `account <id> chat send <room> <message>`
* get a list of commands with `help`


## Usage

See `nuqql-matrixd-nio --help` for a list of command line arguments:

```
usage: nuqql-matrixd-nio [--address ADDRESS] [--af {inet,unix}] [-d] [--dir
DIR] [--disable-history] [--filter-own] [-h] [--loglevel
{debug,info,warn,error}] [--port PORT] [--push-accounts] [--sockfile SOCKFILE]
[--version]

Run nuqql backend matrixd-nio.

optional arguments:
  --address ADDRESS     set AF_INET listen address
  --af {inet,unix}      set socket address family: "inet" for AF_INET, "unix"
                        for AF_UNIX
  -d, --daemonize       daemonize process
  --dir DIR             set working directory
  --disable-history     disable message history
  --filter-own          enable filtering of own messages
  -h, --help            show this help message and exit
  --loglevel {debug,info,warn,error}
                        set logging level
  --port PORT           set AF_INET listen port
  --push-accounts       enable pushing accounts to client
  --sockfile SOCKFILE   set AF_UNIX socket file in DIR
  --version             show program's version number and exit
```


## Changes

* v0.3.3:
  * Update matrix-nio to v0.21.2
* v0.3.2:
  * Update matrix-nio to v0.20.1
* v0.3.1:
  * Update matrix-nio to v0.20.0
* v0.3.0:
  * Update matrix-nio to v0.19.0
* v0.2.0:
  * Update nuqql-based to v0.3.0, switch to asyncio, require python
    version >= 3.7.
  * Add welcome and account adding help messages.
  * Disable filtering of own messages, rewrite sender of own messages to
    `<self>`
* v0.1.0:
  * First/initial release.
