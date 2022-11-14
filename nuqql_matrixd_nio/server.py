"""
matrixd backend server
"""

import html
import re

from typing import TYPE_CHECKING, Dict, Optional, Tuple

# nuqql-based imports
from nuqql_based.based import Based
from nuqql_based.callback import Callback
from nuqql_based.message import Message

# matrixd imports
from nuqql_matrixd_nio.client import BackendClient
from nuqql_matrixd_nio.matrix import unescape_name

if TYPE_CHECKING:   # imports for typing
    # pylint: disable=ungrouped-imports
    from nuqql_based.based import CallbackList
    from nuqql_based.account import Account  # noqa


# matrixd version
VERSION = "0.3.2"


class BackendServer:
    """
    Backend server class, manages the BackendClients for connections to
    IM networks
    """

    def __init__(self) -> None:
        self.connections: Dict[int, BackendClient] = {}
        self.based = Based("matrixd-nio", VERSION)

    async def start(self) -> None:
        """
        Start server
        """

        # set callbacks
        callbacks: "CallbackList" = [
            # based events
            (Callback.BASED_INTERRUPT, self.based_interrupt),
            (Callback.BASED_QUIT, self.based_quit),

            # nuqql messages
            (Callback.QUIT, self.stop_task),
            (Callback.HELP_WELCOME, self._help_welcome),
            (Callback.HELP_ACCOUNT_ADD, self._help_account_add),
            (Callback.ADD_ACCOUNT, self.add_account),
            (Callback.DEL_ACCOUNT, self.del_account),
            (Callback.GET_BUDDIES, self.handle_command),
            (Callback.SEND_MESSAGE, self.send_message),
            (Callback.SET_STATUS, self.handle_command),
            (Callback.GET_STATUS, self.handle_command),
            (Callback.CHAT_LIST, self.handle_command),
            (Callback.CHAT_JOIN, self.handle_command),
            (Callback.CHAT_PART, self.handle_command),
            (Callback.CHAT_SEND, self.chat_send),
            (Callback.CHAT_USERS, self.handle_command),
            (Callback.CHAT_INVITE, self.handle_command),
        ]
        self.based.set_callbacks(callbacks)

        # start based
        await self.based.start()

    async def handle_command(self, account: Optional["Account"], cmd: Callback,
                             params: Tuple) -> str:
        """
        Handle command in account/client
        """

        assert account
        try:
            client = self.connections[account.aid]
        except KeyError:
            # no active connection
            return ""

        await client.handle_command(cmd, params)

        return ""

    async def send_message(self, account: Optional["Account"], cmd: Callback,
                           params: Tuple) -> str:
        """
        send a message to a destination  on an account
        """

        # parse parameters
        if len(params) > 2:
            dest, msg, msg_type = params
        else:
            dest, msg = params
            msg_type = "chat"

        # nuqql sends a html-escaped message; construct "plain-text" version
        # and xhtml version using nuqql's message and use them as message body
        # later
        html_msg = f'<body xmlns="http://www.w3.org/1999/xhtml">{msg}</body>'
        msg = html.unescape(msg)
        msg = "\n".join(re.split("<br/>", msg, flags=re.IGNORECASE))

        # send message
        await self.handle_command(account, cmd, (unescape_name(dest), msg,
                                                 html_msg, msg_type))

        return ""

    async def chat_send(self, account: Optional["Account"], _cmd: Callback,
                        params: Tuple) -> str:
        """
        Send message to chat on account
        """

        chat, msg = params
        # TODO: use cmd to infer msg type in send_message and remove this
        # function?
        return await self.send_message(account, Callback.SEND_MESSAGE,
                                       (chat, msg, "groupchat"))

    async def add_account(self, account: Optional["Account"], _cmd: Callback,
                          _params: Tuple) -> str:
        """
        Add a new account (from based) and run a new client task for it
        """

        # only handle matrix accounts
        assert account
        if account.type != "matrix":
            return ""

        # init client connection
        client = BackendClient(account)

        # save client connection in active connections dictionary
        self.connections[account.aid] = client

        # start client
        await client.start()

        return ""

    async def del_account(self, account: Optional["Account"], _cmd: Callback,
                          _params: Tuple) -> str:
        """
        Delete an existing account (in based) and
        stop matrix client task for it
        """

        # let client clean up
        assert account
        client = self.connections[account.aid]
        await client.stop()
        client.del_account()

        # cleanup
        del self.connections[account.aid]

        return ""

    @staticmethod
    async def _help_account_add(_account: Optional["Account"],
                                _cmd: Callback, _params: Tuple) -> str:
        """
        Handle account add help event
        """

        add_help = Message.info("You do not have any accounts configured.")
        add_help += Message.info("You can add a new matrix account with the "
                                 "following command: "
                                 "account add matrix <username>@<homeserver> "
                                 "<password>")
        add_help += Message.info("Example: account add matrix "
                                 "dummy@matrix.org MyPassword")
        return add_help

    async def _help_welcome(self, _account: Optional["Account"],
                            _cmd: Callback, _params: Tuple) -> str:
        """
        Handle welcome help message event
        """

        welcome = Message.info(f"Welcome to nuqql-matrixd-nio v{VERSION}!")
        welcome += Message.info("Enter \"help\" for a list of available "
                                "commands and their help texts")
        if self.based.config.get_push_accounts():
            welcome += Message.info("Listing your accounts:")
        return welcome

    async def stop_task(self, account: Optional["Account"], _cmd: Callback,
                        _params: Tuple) -> str:
        """
        Quit backend/stop client task
        """

        # stop task
        print("Signalling account tasks to stop.")
        assert account
        client = self.connections[account.aid]
        await client.stop()
        return ""

    async def based_interrupt(self, _account: Optional["Account"],
                              _cmd: Callback, _params: Tuple) -> str:
        """
        KeyboardInterrupt event in based
        """

        for client in self.connections.values():
            print("Signalling account task to stop.")
            await client.stop()
        return ""

    async def based_quit(self, _account: Optional["Account"], _cmd: Callback,
                         _params: Tuple) -> str:
        """
        Based shut down event
        """

        print("Waiting for all tasks to finish. This might take a while.")
        for client in self.connections.values():
            assert client.task
            await client.task
        return ""
