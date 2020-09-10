"""
matrix specific stuff
"""

import asyncio
import logging
import os
import urllib.parse

from typing import Callable, Dict, List, Tuple

from nio import (  # type: ignore
    AsyncClient,
    AsyncClientConfig,
    JoinError,
    JoinedMembersResponse,
    LocalProtocolError,
    LoginResponse,
    MatrixRoom,
    ProfileGetDisplayNameResponse,
    RoomCreateError,
    RoomInviteError,
    RoomLeaveError,
    RoomMemberEvent,
    RoomMessageText
)


class MatrixClient:
    """
    Matrix client class
    """

    def __init__(self, url: str, username: str, store_path: str,
                 message_handler: Callable,
                 membership_handler: Callable) -> None:
        if not os.path.isdir(store_path):
            os.mkdir(store_path)
        self.config = AsyncClientConfig(
            store_sync_tokens=True,
            encryption_enabled=True,
        )
        self.client = AsyncClient(url, username,
                                  store_path=store_path,
                                  config=self.config,
                                  )
        self.client.add_event_callback(self.message_callback, RoomMessageText)
        self.client.add_event_callback(self.member_callback, RoomMemberEvent)
        self.token = ""
        self.status = "offline"

        # handlers
        self.message_handler = message_handler
        self.membership_handler = membership_handler

    async def message_callback(self, room: MatrixRoom,
                               event: RoomMessageText) -> None:
        """
        Message handler
        """

        # save timestamp and message in messages list and history
        tstamp = str(int(event.server_timestamp/1000))
        self.message_handler(tstamp, event.sender, room.machine_name,
                             event.body)

    async def member_callback(self, room: MatrixRoom,
                              event: RoomMemberEvent) -> None:
        """
        Room membership event handler
        """

        tstamp = str(int(event.server_timestamp/1000))

        # set display name of user
        display_name = room.user_name(event.sender)
        if event.membership == "leave":
            resp = await self.client.get_displayname(event.sender)
            if isinstance(resp, ProfileGetDisplayNameResponse):
                if resp.displayname:
                    display_name = resp.displayname

        # set invited user
        invited_user = ""
        if event.membership == "invite":
            invited_user = event.content["displayname"]
        if event.membership == "join":
            invited_user = event.content["displayname"]

        self.membership_handler(event.membership, tstamp, event.sender,
                                display_name, room.room_id, room.display_name,
                                invited_user)

    async def connect(self, password: str, sync_token: str) -> str:
        """
        Connect to matrix server
        """

        resp = await self.client.login(password)
        if isinstance(resp, LoginResponse):
            self.status = "online"

            # start sync task
            sync_filter = {"room": {"timeline": {"limit": 0}}}
            await self.client.sync(timeout=30000, full_state=True,
                                   sync_filter=sync_filter)
            asyncio.create_task(self.client.sync_forever(
                timeout=30000,
                sync_filter={},
                first_sync_filter={},
                since=sync_token,
                full_state=True,
            ))

        return self.status  # remove return?

    def stop(self) -> None:
        """
        Stop client
        """

    def sync_token(self) -> str:
        """
        Get sync token of client connection
        """

        return self.client.next_batch

    def get_rooms(self) -> Dict:
        """
        Get list of rooms
        """

        return self.client.rooms

    def get_invites(self) -> Dict:
        """
        Get room invites
        """

        return self.client.invited_rooms

    @staticmethod
    def get_display_name(user: str) -> str:
        """
        Get the display name of user
        """

        return user

    async def send_message(self, dest_room: str, msg: str,
                           html_msg: str) -> None:
        """
        Send msg to dest_room
        """

        rooms = self.get_rooms()
        for room in rooms.values():
            if dest_room in (room.display_name, room.room_id):
                try:
                    await self.client.room_send(
                        room_id=room.room_id,
                        message_type="m.room.message",
                        content={
                            "msgtype": "m.text",
                            "format": "org.matrix.custom.html",
                            "formatted_body": html_msg,
                            "body": msg,
                        },
                        ignore_unverified_devices=True,
                    )
                except LocalProtocolError as error:
                    logging.error(error)
                    self.status = "offline"

    async def create_room(self, room_name: str) -> str:
        """
        Create chat room that is identified by room_name
        """

        resp = await self.client.room_create(name=room_name)
        if isinstance(resp, RoomCreateError):
            return str(resp)
        return ""

    async def join_room(self, room_name: str) -> str:
        """
        Join chat room that is identified by room_name
        """

        room_name = unescape_name(room_name)
        resp = await self.client.join(room_name)
        if isinstance(resp, JoinError):
            # joining an existing room failed.
            # if chat is not a room id, try to create a new room
            if not room_name.startswith("!") or ":" not in room_name:
                return await self.create_room(room_name)
            return str(resp)
        return ""

    async def _part_room(self, rooms: Dict[str, MatrixRoom],
                         room_name: str) -> str:
        # if room_name is in the rooms dictionary, try to leave/reject it
        for room in rooms.values():
            if unescape_name(room_name) == room.display_name or \
               unescape_name(room_name) == room.room_id:
                # leave room
                resp = await self.client.room_leave(room.room_id)
                if isinstance(resp, RoomLeaveError):
                    return str(resp)
                return ""
        return "NOT FOUND"

    async def part_room(self, room_name: str) -> str:
        """
        Leave chat room identified by room_name
        """

        # part an already joined room
        rooms = self.get_rooms()
        resp = await self._part_room(rooms, room_name)
        if resp == "" or resp != "NOT FOUND":
            return resp

        # part a room we are invited to
        rooms = self.get_invites()
        resp = await self._part_room(rooms, room_name)
        if resp == "NOT FOUND":
            return f"room {room_name} not found"
        return resp

    async def list_room_users(self, room_name: str) -> List[Tuple[str, str,
                                                                  str]]:
        """
        List users in room identified by room_name
        """

        rooms = self.get_rooms()
        user_list: List[Tuple[str, str, str]] = []
        for room in rooms.values():
            if unescape_name(room_name) == room.display_name or \
               unescape_name(room_name) == room.room_id:
                # list members
                resp = await self.client.joined_members(room.room_id)
                if not isinstance(resp, JoinedMembersResponse):
                    return user_list
                for member in resp.members:
                    user_list.append((member.user_id,
                                      escape_name(member.display_name),
                                      "join"))

        return user_list

    async def invite_room(self, room_name: str, user_id: str) -> str:
        """
        Invite user with user_id to room with room_name
        """

        rooms = self.get_rooms()
        for room in rooms.values():
            if unescape_name(room_name) == room.display_name or \
               unescape_name(room_name) == room.room_id:
                resp = await self.client.room_invite(room.room_id, user_id)
                if isinstance(resp, RoomInviteError):
                    return str(resp)
        return ""


def escape_name(name: str) -> str:
    """
    Escape "invalid" charecters in name, e.g., space.
    """

    # escape spaces etc.
    return urllib.parse.quote(name)


def unescape_name(name: str) -> str:
    """
    Convert name back to unescaped version.
    """

    # unescape spaces etc.
    return urllib.parse.unquote(name)


def parse_account_user(acc_user: str) -> Tuple[str, str, str]:
    """
    Parse the user configured in the account to extract the matrix user, domain
    and base url
    """

    # get user name and homeserver part from account user
    user, homeserver = acc_user.split("@", maxsplit=1)

    if homeserver.startswith("http://") or homeserver.startswith("https://"):
        # assume homeserver part contains url
        url = homeserver

        # extract domain name, strip http(s) from homeserver name
        domain = homeserver.split("//", maxsplit=1)[1]

        # strip port from remaining domain name
        domain = domain.split(":", maxsplit=1)[0]
    else:
        # assume homeserver part only contains the domain
        domain = homeserver

        # construct url, default to https
        url = "https://" + domain

    return url, user, domain
