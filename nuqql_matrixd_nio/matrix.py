"""
matrix specific stuff
"""

import asyncio
import json
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
    RoomEncryptedAudio,
    RoomEncryptedFile,
    RoomEncryptedImage,
    RoomEncryptedMedia,
    RoomEncryptedVideo,
    RoomInviteError,
    RoomLeaveError,
    RoomMemberEvent,
    RoomMessage,
    RoomMessageAudio,
    RoomMessageEmote,
    RoomMessageFile,
    RoomMessageFormatted,
    RoomMessageImage,
    RoomMessageMedia,
    RoomMessageNotice,
    RoomMessageText,
    RoomMessageUnknown,
    RoomMessageVideo,
)

# file/directory name settings
STORE_DIR_SUFFIX = "_store"
CREDENTIALS_FILE_SUFFIX = "_credentials.json"

# filter own messages?
FILTER_OWN = True


class MatrixClient:
    """
    Matrix client class
    """

    def __init__(self, url: str, username: str, path: str,
                 handlers: Tuple[Callable, ...]) -> None:
        self.url = url
        self.user = username
        self.path = path
        store_path = path + STORE_DIR_SUFFIX
        if not os.path.isdir(store_path):
            os.mkdir(store_path)
        config = AsyncClientConfig(
            store_sync_tokens=True,
            encryption_enabled=True,
        )
        self.client = AsyncClient(url, username,
                                  store_path=store_path,
                                  config=config,
                                  )
        self.client.add_event_callback(self.message_callback, RoomMessage)
        self.client.add_event_callback(self.member_callback, RoomMemberEvent)
        self.status = "offline"

        # handlers
        message_handler, membership_handler = handlers
        self.message_handler = message_handler
        self.membership_handler = membership_handler

    async def message_callback(self, room: MatrixRoom,
                               event: RoomMessage) -> None:
        """
        Message handler
        """

        # if filter own is set, skip own messages
        if FILTER_OWN and event.sender == self.user:
            if event.transaction_id:
                # only events from this client/device have a transaction ID;
                # only filter these messages, so we still get our own messages
                # from our other devices
                return

        # all (e2ee) media
        if isinstance(event, (RoomMessageMedia, RoomEncryptedMedia)):
            media_mxc = event.url
            media_url = await self.client.mxc_to_http(media_mxc)
            msg_url = " [" + media_url + "]"

        # handle media/message types
        if isinstance(event, (RoomEncryptedAudio, RoomMessageAudio)):
            msg = "*** posted audio: " + event.body + msg_url + " ***"
        elif isinstance(event, RoomMessageEmote):
            msg = "*** posted emote: " + event.body + " ***"
        elif isinstance(event, (RoomEncryptedFile, RoomMessageFile)):
            msg = "*** posted file: " + event.body + msg_url + " ***"
        elif isinstance(event, (RoomMessageFormatted, RoomMessageNotice,
                                RoomMessageText)):
            msg = event.body
        elif isinstance(event, (RoomEncryptedImage, RoomMessageImage)):
            # Usually body is something like "image.svg"
            msg = "*** posted image: " + event.body + msg_url + " ***"
        elif isinstance(event, RoomMessageUnknown):
            msg = "*** sent room message of unknown type: " + event.msgtype + \
                    " ***"
        elif isinstance(event, (RoomEncryptedVideo, RoomMessageVideo)):
            msg = "*** posted video: " + event.body + msg_url + " ***"

        # save timestamp and message in messages list and history
        tstamp = str(int(event.server_timestamp/1000))
        self.message_handler(tstamp, event.sender, room.machine_name, msg)

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

    def save_credentials(self, user_id: str, device_id: str,
                         access_token: str) -> None:
        """
        save credentials like access token to disk for later logins
        """

        # open the config file in write-mode
        with open(self.path + CREDENTIALS_FILE_SUFFIX, "w") as cred_file:
            # write the login details to disk
            json.dump({
                "homeserver": self.url,  # e.g. "https://matrix.example.org"
                "user_id": user_id,  # e.g. "@user:example.org"
                "device_id": device_id,  # device ID, 10 uppercase letters
                "access_token": access_token  # cryptogr. access token
                }, cred_file)

    def get_credentials(self) -> Tuple[str, str, str]:
        """
        read previously saved credentials from disk
        """

        credentials_file = self.path + CREDENTIALS_FILE_SUFFIX
        if os.path.exists(credentials_file):
            with open(credentials_file, "r") as cred_file:
                creds = json.load(cred_file)
                return (creds["user_id"], creds["device_id"],
                        creds["access_token"])
        return ("", "", "")

    async def sync_task(self, sync_token: str) -> None:
        """
        Start sync forever task
        """

        await self.client.sync_forever(
            timeout=30000,
            sync_filter={},
            first_sync_filter={},
            since=sync_token,
            full_state=True,
        )

        # if sync_forever() terminates, something went wrong and we are
        # probably offline. Set status to offline and trigger reconnect
        logging.error("sync task stopped")
        self.status = "offline"

    async def connect(self, password: str, sync_token: str) -> str:
        """
        Connect to matrix server
        """

        # try to restore previous login
        user_id, device_id, access_token = self.get_credentials()
        if access_token != "":
            self.client.restore_login(
                user_id=user_id,
                device_id=device_id,
                access_token=access_token,
                )
            self.status = "online"
        else:
            resp = await self.client.login(password,
                                           device_name="nuqql-matrixd-nio")
            if isinstance(resp, LoginResponse):
                self.status = "online"

                # save credentials
                self.save_credentials(resp.user_id, resp.device_id,
                                      resp.access_token)

        if self.status == "online":
            # start sync task
            sync_filter = {"room": {"timeline": {"limit": 0}}}
            await self.client.sync(timeout=30000, full_state=True,
                                   sync_filter=sync_filter)
            asyncio.create_task(self.sync_task(sync_token))

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
