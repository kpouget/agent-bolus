"""GlookoXT API client for historical diabetes data retrieval.

API contract reverse-engineered from Nightscout/Nocturne PR #1366.
Base URL: https://srv.glookoxt.com
Auth: email + password -> email code -> JWT (~1 year lifetime)
Data: Socket.IO v4 (WebSocket transport) with emit/ack pattern
"""

import asyncio
import base64
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import socketio

BASE_URL = "https://srv.glookoxt.com"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"
TOKEN_BUFFER_MINUTES = 60
FETCH_CHUNK_DAYS = 7
EXPORT_CHUNK_DAYS = 14
SOCKET_TIMEOUT = 60


class GlookoXtAuth:
    def __init__(self, token_path="logindata.json"):
        self.token_path = Path(token_path)
        self.token = None
        self.token_payload = None

    def request_code(self, email, password):
        resp = requests.post(
            f"{BASE_URL}/api/users/patient-login/",
            json={"email": email, "password": password},
            headers={"x-ab-token": "", "Content-Type": "application/json"},
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            raise AuthError(f"Login failed with HTTP {resp.status_code}: {resp.text}")
        data = resp.json()
        if data.get("error"):
            raise AuthError(f"Login rejected: {data['error']}")
        return data

    def redeem_code(self, email, code):
        resp = requests.post(
            f"{BASE_URL}/api/users/code-auth",
            json={"email": email, "code": code},
            headers={"x-ab-token": "", "Content-Type": "application/json"},
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            raise AuthError(f"Code redemption failed with HTTP {resp.status_code}: {resp.text}")
        data = resp.json()
        if data.get("error"):
            raise AuthError(f"Code rejected: {data['error']}")
        token = data.get("token")
        if not token:
            raise AuthError("No token in response")
        self.token = token
        self.token_payload = _decode_jwt_payload(token)
        return data

    def save_token(self, path=None):
        path = Path(path) if path else self.token_path
        path.write_text(json.dumps({
            "token": self.token,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2))

    def load_token(self, path=None):
        path = Path(path) if path else self.token_path
        if not path.exists():
            raise AuthError(f"Token file not found: {path}")
        data = json.loads(path.read_text())
        self.token = data["token"]
        self.token_payload = _decode_jwt_payload(self.token)
        return data

    def is_token_valid(self):
        if not self.token_payload:
            return False
        exp = self.token_payload.get("exp")
        if exp is None:
            return True
        exp = int(exp)
        return time.time() < (exp - TOKEN_BUFFER_MINUTES * 60)

    def token_expiry(self):
        if not self.token_payload:
            return None
        exp = self.token_payload.get("exp")
        if exp is None:
            return None
        return datetime.fromtimestamp(int(exp), tz=timezone.utc)


class GlookoXtData:
    def __init__(self):
        self.sio = None

    async def connect(self, token, debug=False):
        self.sio = socketio.AsyncClient(
            engineio_logger=debug,
            logger=debug,
            reconnection=False,
        )
        if debug:
            @self.sio.event
            async def connect_error(data):
                print(f"[DEBUG] connect_error event: {data}")

        await self.sio.connect(
            f"{BASE_URL}?token={token}",
            transports=["websocket"],
            socketio_path="/socket.io",
            wait_timeout=SOCKET_TIMEOUT,
        )

    async def disconnect(self):
        if self.sio and self.sio.connected:
            await self.sio.disconnect()

    async def get_user_data(self):
        resp = await self.sio.call("GET_USER_DATA", {}, timeout=SOCKET_TIMEOUT)
        return _parse_response(resp)

    async def get_collected_data(self, start, end):
        all_records = []
        seen_ids = set()
        chunk_start = start
        while chunk_start < end:
            chunk_end = min(chunk_start + timedelta(days=FETCH_CHUNK_DAYS), end)
            payload = {
                "start_time": chunk_start.strftime(DATE_FORMAT),
                "end_time": chunk_end.strftime(DATE_FORMAT),
            }
            resp = await self.sio.call("GET_COLLECTED_DATA", payload, timeout=SOCKET_TIMEOUT)
            parsed = _parse_response(resp)
            records = _extract_records(parsed)
            for r in records:
                rid = r.get("id")
                if rid is not None and rid not in seen_ids:
                    seen_ids.add(rid)
                    all_records.append(r)
                elif rid is None:
                    all_records.append(r)
            chunk_start = chunk_end
        return all_records

    async def get_export(self, start, end):
        all_csv = []
        chunk_start = start - timedelta(days=1)
        while chunk_start < end + timedelta(days=1):
            chunk_end = min(chunk_start + timedelta(days=EXPORT_CHUNK_DAYS), end + timedelta(days=1))
            payload = {
                "start_date": chunk_start.strftime("%Y-%m-%d"),
                "end_date": chunk_end.strftime("%Y-%m-%d"),
            }
            resp = await self.sio.call("EXPORT_RECORDS", payload, timeout=SOCKET_TIMEOUT)
            parsed = _parse_response(resp)
            csv_text = _extract_export(parsed)
            if csv_text:
                all_csv.append(csv_text)
            chunk_start = chunk_end
        return "\n".join(all_csv)

    async def get_products(self, product_type="pump"):
        resp = await self.sio.call("GET_PRODUCTS", {"product_type": product_type}, timeout=SOCKET_TIMEOUT)
        return _parse_response(resp)


class AuthError(Exception):
    pass


def _decode_jwt_payload(token):
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthError("Invalid JWT format")
    payload_b64 = parts[1]
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    return json.loads(base64.urlsafe_b64decode(payload_b64))


def _parse_response(resp):
    """Handle the three response shapes from GlookoXT:
    1. Object with a known key (collected_data, export, profile, brands, etc.)
    2. Bare array or string
    3. Double-encoded JSON string
    """
    if isinstance(resp, str):
        try:
            resp = json.loads(resp)
        except (json.JSONDecodeError, TypeError):
            return resp
    if isinstance(resp, dict) and resp.get("error"):
        raise RuntimeError(f"GlookoXT error: {resp['error']}")
    return resp


def _extract_records(parsed):
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        if "collected_data" in parsed:
            data = parsed["collected_data"]
            if isinstance(data, str):
                data = json.loads(data)
            return data if isinstance(data, list) else []
    return []


def _extract_export(parsed):
    if isinstance(parsed, str):
        return parsed
    if isinstance(parsed, dict):
        if "export" in parsed:
            export = parsed["export"]
            if isinstance(export, str):
                return export
    return ""
