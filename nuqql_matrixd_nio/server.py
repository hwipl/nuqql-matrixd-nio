"""
matrixd backend server
"""

import asyncio
import html
import re

from typing import TYPE_CHECKING, Dict, Optional, Tuple
from threading import Event

# nuqq-based imports
from nuqql_based.based import Based
from nuqql_based.callback import Callback

# matrixd imports
from nuqql_matrixd_nio.client import BackendClient
from nuqql_matrixd_nio.matrix import unescape_name

if TYPE_CHECKING:   # imports for typing
    # pylint: disable=ungrouped-imports
    from nuqql_based.account import Account  # noqa


# matrixd version
VERSION = "0.1.0"


class BackendServer:
    """
    Backend server class, manages the BackendClients for connections to
    IM networks
    """

    def __init__(self) -> None:
        self.connections: Dict[int, BackendClient] = {}
        self.tasks: Dict[int, Tuple[asyncio.Task, Event]] = {}
        self.based = Based("matrixd-nio", VERSION)

    async def start(self) -> None:
        """
        Start server
        """

        # set callbacks
        callbacks = [
            # based events
            (Callback.BASED_INTERRUPT, self.based_interrupt),
            (Callback.BASED_QUIT, self.based_quit),

            # nuqql messages
            (Callback.QUIT, self.stop_thread),
            (Callback.ADD_ACCOUNT, self.add_account),
            (Callback.DEL_ACCOUNT, self.del_account),
            (Callback.SEND_MESSAGE, self.send_message),
            (Callback.SET_STATUS, self.enqueue),
            (Callback.GET_STATUS, self.enqueue),
            (Callback.CHAT_LIST, self.enqueue),
            (Callback.CHAT_JOIN, self.enqueue),
            (Callback.CHAT_PART, self.enqueue),
            (Callback.CHAT_SEND, self.chat_send),
            (Callback.CHAT_USERS, self.enqueue),
            (Callback.CHAT_INVITE, self.enqueue),
        ]
        self.based.set_callbacks(callbacks)

        # start based
        await self.based.start()

    def enqueue(self, account: Optional["Account"], cmd: Callback,
                params: Tuple) -> str:
        """
        add commands to the command queue of the account/client
        """

        assert account
        try:
            client = self.connections[account.aid]
        except KeyError:
            # no active connection
            return ""

        client.enqueue_command(cmd, params)

        return ""

    def send_message(self, account: Optional["Account"], cmd: Callback,
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
        html_msg = \
            '<body xmlns="http://www.w3.org/1999/xhtml">{}</body>'.format(msg)
        msg = html.unescape(msg)
        msg = "\n".join(re.split("<br/>", msg, flags=re.IGNORECASE))

        # send message
        self.enqueue(account, cmd, (unescape_name(dest), msg, html_msg,
                                    msg_type))

        return ""

    def chat_send(self, account: Optional["Account"], _cmd: Callback,
                  params: Tuple) -> str:
        """
        Send message to chat on account
        """

        chat, msg = params
        # TODO: use cmd to infer msg type in send_message and remove this
        # function?
        return self.send_message(account, Callback.SEND_MESSAGE,
                                 (chat, msg, "groupchat"))

    def add_account(self, account: Optional["Account"], _cmd: Callback,
                    _params: Tuple) -> str:
        """
        Add a new account (from based) and run a new client task for it
        """

        # only handle matrix accounts
        assert account
        if account.type != "matrix":
            return ""

        # event to signal if task should stop
        running = Event()
        running.set()

        # init client connection
        client = BackendClient(account)

        # save client connection in active connections dictionary
        self.connections[account.aid] = client

        # create and start task
        task = asyncio.create_task(client.start(running))

        # save task in active tasks dictionary
        self.tasks[account.aid] = (task, running)

        return ""

    def del_account(self, account: Optional["Account"], _cmd: Callback,
                    _params: Tuple) -> str:
        """
        Delete an existing account (in based) and
        stop matrix client thread for it
        """

        # stop thread
        assert account
        task, running = self.tasks[account.aid]
        running.clear()
        asyncio.gather(task)

        # let client clean up
        client = self.connections[account.aid]
        client.del_account()

        # cleanup
        del self.connections[account.aid]
        del self.tasks[account.aid]

        return ""

    def stop_thread(self, account: Optional["Account"], _cmd: Callback,
                    _params: Tuple) -> str:
        """
        Quit backend/stop client thread
        """

        # stop thread
        assert account
        print("Signalling account tasks to stop.")
        _task, running = self.tasks[account.aid]
        running.clear()
        return ""

    def based_interrupt(self, _account: Optional["Account"], _cmd: Callback,
                        _params: Tuple) -> str:
        """
        KeyboardInterrupt event in based
        """

        for _task, running in self.tasks.values():
            print("Signalling account task to stop.")
            running.clear()
        return ""

    def based_quit(self, _account: Optional["Account"], _cmd: Callback,
                   _params: Tuple) -> str:
        """
        Based shut down event
        """

        print("Waiting for all tasks to finish. This might take a while.")
        for task, _running in self.tasks.values():
            asyncio.gather(task)
        return ""
