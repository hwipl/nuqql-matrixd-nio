#!/usr/bin/env python3

"""
matrixd main entry point
"""

from nuqql_matrixd_nio.server import BackendServer


def main() -> None:
    """
    Main function, initialize everything and start server
    """

    server = BackendServer()
    server.start()


if __name__ == '__main__':
    main()
