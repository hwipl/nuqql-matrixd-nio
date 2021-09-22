"""
matrixd backend client
"""

import asyncio

from typing import TYPE_CHECKING, Optional, Tuple
from types import SimpleNamespace

# nuqq-based imports
from nuqql_based.message import Message
from nuqql_based.callback import Callback

# matrixd import
from nuqql_matrixd_nio.matrix import (MatrixClient,
                                      escape_name)

if TYPE_CHECKING:   # imports for typing
    # pylint: disable=ungrouped-imports
    from nuqql_based.account import Account  # noqa


class BackendClient:
    """
    Backend Client Class for connections to the IM network
    """

    def __init__(self, account: "Account") -> None:
        # account
        self.account = account

        # initialize matrix client connection
        self.client = MatrixClient(account,
                                   (self._message, self._membership_event))

        # client task
        self.task: Optional[asyncio.Task] = None

        # is client active?
        self.active = True

        # sync token and connection config
        self.settings = SimpleNamespace(
            # Send regular message to client for membership events?
            membership_message_msg=True,
            # Send user message to client for membership events?
            membership_user_msg=True,
        )

    async def _start(self) -> None:
        """
        Start the client as a task
        """

        # enter main loop
        try:
            while True:
                # if client is offline, (re)connect
                if self.client.status == "offline":
                    # start client connection
                    await self.client.connect(self.account.password)

                # stop, if client is inactive
                if not self.active:
                    return

                # sleep a little bit before reconnecting
                await asyncio.sleep(15)
        except asyncio.CancelledError:
            # close underlying http session
            await self.client.client.close()
            return

    async def start(self) -> None:
        """
        Start the client
        """

        # create and start task
        self.task = asyncio.create_task(self._start())

    async def stop(self) -> None:
        """
        Stop the client
        """

        self.active = False
        assert self.task
        self.task.cancel()
        await self.task

    def _membership_event(self, *params):
        """
        Handle membership event
        """

        # parse params
        event_type, tstamp, sender_id, sender_name, room_id, room_name,\
            invited_user = params

        # check membership type
        if event_type == "invite":
            user_msg = Message.chat_user(self.account, room_id, invited_user,
                                         invited_user, event_type)
            msg = (f"*** {sender_name} invited {invited_user} "
                   f"to {room_name}. ***")

        if event_type == "join":
            user_msg = Message.chat_user(self.account, room_id, sender_id,
                                         invited_user, event_type)
            msg = f"*** {invited_user} joined {room_name}. ***"

        if event_type == "leave":
            user_msg = Message.chat_user(self.account, room_id, sender_id,
                                         sender_name, event_type)
            msg = f"*** {sender_name} left {room_name}. ***"

        # generic event, return as message
        # TODO: change parsing in nuqql and use char + / + sender here?
        formatted_msg = Message.CHAT_MSG.format(self.account.aid, room_id,
                                                tstamp, sender_id, msg)

        # add event to event list
        if self.settings.membership_user_msg:
            self.account.receive_msg(user_msg)
        if self.settings.membership_message_msg:
            self.account.receive_msg(formatted_msg)

    def _message(self, tstamp, sender, room_id, msg) -> None:
        """
        Message handler
        """

        # save timestamp and message in messages list and history
        formatted_msg = Message.chat_msg(self.account, tstamp, sender, room_id,
                                         msg)
        self.account.receive_msg(formatted_msg)

    def muc_message(self, msg) -> None:
        """
        Groupchat message handler.
        """
        # TODO: if we do nothing extra here, move it into normal message
        # handler above?

    def _muc_presence(self, presence, status) -> None:
        """
        Group chat presence handler
        """

        # get chat and our nick in the chat

    def muc_online(self, presence) -> None:
        """
        Group chat online presence handler
        """

        self._muc_presence(presence, "online")

    def muc_offline(self, presence) -> None:
        """
        Group chat offline presence handler
        """

        self._muc_presence(presence, "offline")

    async def handle_command(self, cmd: Callback, params: Tuple) -> None:
        """
        Handle a command
        Params tuple consists of:
            command and its parameters
        """

        if cmd == Callback.GET_BUDDIES:
            self.get_buddies(params[0])
        if cmd == Callback.SEND_MESSAGE:
            await self._send_message(params)
        if cmd == Callback.SET_STATUS:
            self._set_status(params[0])
        if cmd == Callback.GET_STATUS:
            self._get_status()
        if cmd == Callback.CHAT_LIST:
            self._chat_list()
        if cmd == Callback.CHAT_JOIN:
            await self._chat_join(params[0])
        if cmd == Callback.CHAT_PART:
            await self._chat_part(params[0])
        if cmd == Callback.CHAT_USERS:
            await self._chat_users(params[0])
        if cmd == Callback.CHAT_INVITE:
            await self._chat_invite(params[0], params[1])

    async def _send_message(self, message_tuple: Tuple) -> None:
        """
        Send a single message
        """

        # if we are offline, send nothing
        # TODO: remove this?
        if self.client.status == "offline":
            return

        # create message from message tuple and send it
        dest, msg, html_msg, _mtype = message_tuple
        await self.client.send_message(dest, msg, html_msg)

    def _set_status(self, status: str) -> None:
        """
        Set the current status of the account
        """

        # TODO: do something when status changes, e.g., from offline to online?
        self.client.status = status

    def _get_status(self) -> None:
        """
        Get the current status of the account
        """

        self.account.receive_msg(Message.status(self.account,
                                                self.client.status))

    def _chat_list(self) -> None:
        """
        List active chats of account
        """

        rooms = self.client.get_rooms()
        for room in rooms.values():
            self.account.receive_msg(Message.chat_list(
                self.account, room.room_id, escape_name(room.display_name),
                self.client.get_user()))

    async def _chat_create(self, name: str) -> None:
        """
        Create a group chat room with name <name>
        """

        # TODO: check if this is really used and remove it?
        error = await self.client.create_room(name)
        if error != "":
            self.account.receive_msg(Message.error(error))

    async def _chat_join(self, chat: str) -> None:
        """
        Join chat on account
        """

        error = await self.client.join_room(chat)
        if error != "":
            self.account.receive_msg(Message.error(error))

    async def _chat_part(self, chat: str) -> None:
        """
        Leave chat on account
        """

        error = await self.client.part_room(chat)
        if error != "":
            self.account.receive_msg(Message.error(error))

    async def _chat_users(self, chat: str) -> None:
        """
        Get list of users in chat on account
        """

        user_list = await self.client.list_room_users(chat)
        for user in user_list:
            user_id, user_name, user_status = user
            self.account.receive_msg(
                Message.chat_user(self.account, chat, user_id, user_name,
                                  user_status))

    async def _chat_invite(self, chat: str, user_id: str) -> None:
        """
        Invite user to chat
        """

        error = await self.client.invite_room(chat, user_id)
        if error != "":
            self.account.receive_msg(Message.error(error))

    def get_buddies(self, online: bool) -> None:
        """
        get roster/buddy list
        """

        # if we are offline, there are no buddies
        if self.client.status == "offline":
            return

        # if only online wanted, skip because no matrix room is "online"
        if online:
            return

        # get buddies/rooms
        rooms = self.client.get_rooms()
        for room in rooms.values():
            name = escape_name(room.display_name)

            # use special status for group chats
            status = "GROUP_CHAT"

            # send buddy message
            msg = Message.buddy(self.account, room.room_id, name, status)
            self.account.receive_msg(msg)

        # handle pending room invites as temporary buddies
        invites = self.client.get_invites()
        for invite in invites.values():
            status = "GROUP_CHAT_INVITE"

            # send buddy message
            msg = Message.buddy(self.account, invite.room_id,
                                invite.display_name, status)
            self.account.receive_msg(msg)

    def del_account(self):
        """
        Cleanup after account deletion
        """

        self.client.delete_sync_token()
