"""
matrix specific stuff
"""

import urllib.parse

from typing import Any, Callable, Dict, List, Tuple

from nio import AsyncClient, LoginResponse, MatrixRoom, RoomMessageText


class MatrixClient:
    """
    Matrix client class
    """

    def __init__(self, url: str, username: str, message_handler: Callable,
                 membership_handler: Callable) -> None:
        self.client = AsyncClient(url, username)
        self.client.add_event_callback(self.message_callback, RoomMessageText)
        self.token = ""
        self.status = "offline"

        # separate data structure for managing room invites
        self.room_invites: Dict[str, Tuple[str, str, str, str, str]] = {}

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
        self.message_handler(tstamp, room.user_name(event.sender),
                             room.machine_name,
                             event.body)

    async def connect(self, password: str, _sync_token: str) -> str:
        """
        Connect to matrix server
        """
        resp = await self.client.login(password)
        if isinstance(resp, LoginResponse):
            self.status = "online"
        return self.status  # remove return?

    def stop(self) -> None:
        """
        Stop client
        """

    @staticmethod
    def sync_token() -> str:
        """
        Get sync token of client connection
        """

        return ""

    @staticmethod
    def get_rooms() -> Dict:
        """
        Get list of rooms
        """

        rooms: Dict[Any, Any] = {}
        return rooms

    def get_invites(self) -> Dict:
        """
        Get room invites
        """

        # cleanup old invites
        rooms = self.get_rooms()
        for room in rooms.values():
            if room.room_id in self.room_invites:
                # seems like we are in the room now, remove invite
                del self.room_invites[room.room_id]

        return self.room_invites

    @staticmethod
    def get_display_name(user: str) -> str:
        """
        Get the display name of user
        """

        return user

    def send_message(self, dest_room: str, msg: str, html_msg: str) -> None:
        """
        Send msg to dest_room
        """

    @staticmethod
    def create_room(_room_name: str) -> str:
        """
        Create chat room that is identified by room_name
        """

        return ""

    @staticmethod
    def join_room(_room_name: str) -> str:
        """
        Join chat room that is identified by room_name
        """

        return ""

    @staticmethod
    def part_room(_room_name: str) -> str:
        """
        Leave chat room identified by room_name
        """

        return ""

    @staticmethod
    def list_room_users(_room_name: str) -> List[Tuple[str, str, str]]:
        """
        List users in room identified by room_name
        """

        user_list: List[Any] = []
        return user_list

    @staticmethod
    def invite_room(_room_name: str, _user_id: str) -> str:
        """
        Invite user with user_id to room with room_name
        """

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
