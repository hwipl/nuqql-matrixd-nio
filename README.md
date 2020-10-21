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
usage: nuqql-matrixd-nio [-h] [--version] [--af {inet,unix}] [--address
ADDRESS] [--port PORT] [--sockfile SOCKFILE] [--dir DIR] [-d] [--loglevel
{debug,info,warn,error}] [--disable-history] [--push-accounts]

Run nuqql backend.

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --af {inet,unix}      socket address family: "inet" for AF_INET, "unix" for
                        AF_UNIX
  --address ADDRESS     AF_INET listen address
  --port PORT           AF_INET listen port
  --sockfile SOCKFILE   AF_UNIX socket file in DIR
  --dir DIR             working directory
  -d, --daemonize       daemonize process
  --loglevel {debug,info,warn,error}
                        Logging level
  --disable-history     disable message history
  --push-accounts       push accounts to client
```


## Changes

* v0.1.0:
  * First/initial release.
