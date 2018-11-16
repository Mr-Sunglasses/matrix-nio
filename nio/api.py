# -*- coding: utf-8 -*-

# Copyright © 2018 Damir Jelić <poljar@termina.org.uk>
#
# Permission to use, copy, modify, and/or distribute this software for
# any purpose with or without fee is hereby granted, provided that the
# above copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
# SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
# RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF
# CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from __future__ import unicode_literals

import json
from typing import Any, Dict, Optional, Tuple, List, Set, DefaultDict, Union
from enum import Enum, unique
from collections import defaultdict

from .exceptions import LocalProtocolError
from .http import Http2Request, HttpRequest, TransportRequest

if False:
    from uuid import UUID

try:
    from urllib.parse import quote, urlencode, urlparse
except ImportError:
    from urllib import quote, urlencode  # type: ignore
    from urlparse import urlparse  # type: ignore


MATRIX_API_PATH = "/_matrix/client/r0"  # type: str


@unique
class MessageDirection(Enum):
    back = 0
    front = 1


class Api(object):
    @staticmethod
    def to_json(content_dict):
        # type: (Dict[Any, Any]) -> str
        return json.dumps(content_dict, separators=(",", ":"))

    @staticmethod
    def to_canonical_json(content_dict):
        # type: (Dict[Any, Any]) -> str
        return json.dumps(
            content_dict,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    @staticmethod
    def mxc_to_http(mxc):
        # type: (str) -> Optional[str]
        url = urlparse(mxc)

        if url.scheme != "mxc":
            return None

        if not url.netloc or not url.path:
            return None

        http_url = (
            "https://{host}/_matrix/media/r0/download/"
            "{server_name}{mediaId}"
        ).format(host=url.netloc, server_name=url.netloc, mediaId=url.path)

        return http_url

    @staticmethod
    def encrypted_mxc_to_plumb(mxc, key, hash, iv):
        # type: (str, str, str, str) -> Optional[str]
        url = urlparse(mxc)

        if url.scheme != "mxc":
            return None

        if not url.netloc or not url.path:
            return None

        plumb_url = (
            "emxc://{host}/_matrix/media/r0/download/"
            "{server_name}{mediaId}"
        ).format(host=url.netloc, server_name=url.netloc, mediaId=url.path)

        query_parameters = {
            "key": key,
            "hash": hash,
            "iv": iv,
        }

        plumb_url += "?{}".format(urlencode(query_parameters))

        return plumb_url

    @staticmethod
    def _build_path(path, query_parameters=None):
        # type: (str, dict) -> str
        path = ("{api}/{path}").format(api=MATRIX_API_PATH, path=path)

        if query_parameters:
            path += "?{}".format(urlencode(query_parameters))

        return path

    @staticmethod
    def login(user, password, device_name="", device_id=""):
        # type: (str, str, Optional[str], Optional[str]) -> Tuple[str, str]
        path = Api._build_path("login")

        content_dict = {
            "type": "m.login.password",
            "user": user,
            "password": password,
        }

        if device_id:
            content_dict["device_id"] = device_id

        if device_name:
            content_dict["initial_device_display_name"] = device_name

        return "POST", path, Api.to_json(content_dict)

    @staticmethod
    def sync(
        access_token,  # type: str
        next_batch=None,  # type: Optional[str]
        timeout=None,  # type: Optional[int]
        filter=None,  # type: Optional[Dict[Any, Any]]
    ):
        # type: (...) -> str
        query_parameters = {"access_token": access_token}

        if next_batch:
            query_parameters["since"] = next_batch

        if timeout:
            query_parameters["timeout"] = str(timeout)

        if filter:
            filter_json = json.dumps(filter, separators=(",", ":"))
            query_parameters["filter"] = filter_json

        return "GET", Api._build_path("sync", query_parameters)

    @staticmethod
    def room_send(access_token, room_id, msg_type, content, tx_id):
        query_parameters = {"access_token": access_token}

        path = "rooms/{room}/send/{msg_type}/{tx_id}".format(
            room=room_id, msg_type=msg_type, tx_id=tx_id
        )

        return (
            "PUT",
            Api._build_path(path, query_parameters),
            Api.to_json(content)
        )

    @staticmethod
    def room_put_state(access_token, room_id, event_type, body):
        query_parameters = {"access_token": access_token}

        path = "rooms/{room}/state/{event_type}".format(
            room=room_id, event_type=event_type
        )

        return (
            "PUT",
            Api._build_path(path, query_parameters),
            Api.to_json(body)
        )

    @staticmethod
    def room_redact(access_token, room_id, event_id, tx_id, reason=None):
        query_parameters = {"access_token": access_token}

        body = {}

        if reason:
            body["reason"] = reason

        path = "rooms/{room}/redact/{event_id}/{tx_id}".format(
            room=room_id, event_id=event_id, tx_id=tx_id
        )

        return (
            "PUT",
            Api._build_path(path, query_parameters),
            Api.to_json(body)
        )

    @staticmethod
    def room_kick(access_token, room_id, user_id, reason=None):
        query_parameters = {"access_token": access_token}

        body = {"user_id": user_id}

        if reason:
            body["reason"] = reason

        path = "rooms/{room}/kick".format(room=room_id)

        return (
            "POST",
            Api._build_path(path, query_parameters),
            Api.to_json(body)
        )

    @staticmethod
    def room_invite(access_token, room_id, user_id):
        query_parameters = {"access_token": access_token}
        body = {"user_id": user_id}
        path = "rooms/{room}/invite".format(room=room_id)

        return (
            "POST",
            Api._build_path(path, query_parameters),
            Api.to_json(body)
        )

    @staticmethod
    def join(access_token, room_id):
        query_parameters = {"access_token": access_token}
        body = {}
        path = "join/{room}".format(room=room_id)

        return (
            "POST",
            Api._build_path(path, query_parameters),
            Api.to_json(body)
        )

    @staticmethod
    def room_leave(access_token, room_id):
        query_parameters = {"access_token": access_token}
        body = {}
        path = "rooms/{room}/leave".format(room=room_id)

        return (
            "POST",
            Api._build_path(path, query_parameters),
            Api.to_json(body)
        )

    @staticmethod
    def room_messages(
        access_token,
        room_id,
        start,
        end=None,
        direction=MessageDirection.back,
        limit=10,
    ):
        query_parameters = {
            "access_token": access_token,
            "from": start,
            "limit": limit
        }

        if end:
            query_parameters["to"] = end

        if isinstance(direction, str):
            if direction in ("b", "back"):
                direction = MessageDirection.back
            elif direction in ("f", "fron"):
                direction = MessageDirection.front
            else:
                raise ValueError("Invalid direction")

        if direction is MessageDirection.front:
            query_parameters["dir"] = "f"
        else:
            query_parameters["dir"] = "b"

        path = "rooms/{room}/messages".format(room=room_id)

        return "GET", Api._build_path(path, query_parameters)

    @staticmethod
    def keys_upload(access_token, key_dict):
        query_parameters = {"access_token": access_token}
        body = key_dict
        path = "keys/upload"

        return (
            "POST",
            Api._build_path(path, query_parameters),
            Api.to_json(body)
        )

    @staticmethod
    def keys_query(access_token, user_set):
        # type: (str, Set[str]) -> Tuple[str, str]
        query_parameters = {"access_token": access_token}
        path = "keys/query"

        content = {
            "device_keys": {user: [] for user in user_set}
        }  # type: Dict[str, Dict[str, List]]

        return (
            "POST",
            Api._build_path(path, query_parameters),
            Api.to_json(content)
        )

    @staticmethod
    def keys_claim(access_token, user_set):
        # type: (str, Dict[str, List[str]]) -> Tuple[str, str]
        query_parameters = {"access_token": access_token}
        path = "keys/claim"

        payload = defaultdict(dict)  # type: DefaultDict[str, Dict[str, str]]

        for user_id, device_list in user_set.items():
            for device_id in device_list:
                payload[user_id][device_id] = "signed_curve25519"

        content = {
            "one_time_keys": payload
        }

        return (
            "POST",
            Api._build_path(path, query_parameters),
            Api.to_json(content)
        )

    @staticmethod
    def to_device(access_token, event_type, content, tx_id):
        # type: (str, str, Dict[Any, Any], Union[str, UUID]) -> Tuple[str, str]
        query_parameters = {"access_token": access_token}
        path = "sendToDevice/{event_type}/{tx_id}".format(
            event_type=event_type,
            tx_id=tx_id
        )

        return (
            "PUT",
            Api._build_path(path, query_parameters),
            Api.to_json(content)
        )

    @staticmethod
    def devices(access_token):
        # type: (str) -> str
        query_parameters = {"access_token": access_token}
        path = "devices"
        return "GET", Api._build_path(path, query_parameters)

    @staticmethod
    def update_device(access_token, device_id, content):
        # type: (str, Dict[str, str]) -> Tuple[str, str]
        query_parameters = {"access_token": access_token}
        path = "devices/{}".format(device_id)

        return (
            "PUT",
            Api._build_path(path, query_parameters),
            Api.to_json(content)
        )

    @staticmethod
    def delete_devices(access_token, devices, auth_dict=None):
        # type: (str, List[str], Optional[Dict[str, str]]) -> Tuple[str, str]
        query_parameters = {"access_token": access_token}
        path = "delete_devices"

        content = {
            "devices": devices
        }  # type: Dict[str, Any]

        if auth_dict:
            content["auth"] = auth_dict

        return (
            "POST",
            Api._build_path(path, query_parameters),
            Api.to_json(content)
        )

    @staticmethod
    def joined_members(access_token, room_id):
        # type: (str, str) -> str
        query_parameters = {"access_token": access_token}
        path = "rooms/{}/joined_members".format(room_id)

        return "GET", Api._build_path(path, query_parameters)
