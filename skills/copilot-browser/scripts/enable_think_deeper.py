#!/usr/bin/env python3
"""Enable Copilot Think deeper via Chrome DevTools Protocol.

This is a fallback when chrome-devtools snapshot/click actions cannot open
Copilot's Smart mode menu. It connects directly to Chromium's remote debugging
port, finds a Copilot page, clicks the Smart mode button, then clicks the
Think deeper option.

Run this script only after snapshot-driven clicks have failed to open the
mode menu. The script is not the primary path; it is a supplementary fallback.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import struct
import sys
import time
import urllib.request
import urllib.parse


CDP_JSON = "http://127.0.0.1:9222/json"


def choose_copilot_target() -> dict:
    targets = json.loads(urllib.request.urlopen(CDP_JSON, timeout=5).read())
    copilot = [
        target
        for target in targets
        if target.get("type") == "page"
        and "copilot.microsoft.com" in target.get("url", "")
        and target.get("webSocketDebuggerUrl")
    ]
    if not copilot:
        raise SystemExit("No Copilot page found in Chrome CDP targets")

    # Prefer the Copilot home composer if present; otherwise use the first
    # Copilot tab. Agents should navigate to https://copilot.microsoft.com/
    # before running this script for best results.
    return next((target for target in copilot if target.get("url") == "https://copilot.microsoft.com/"), copilot[0])


class CDPWebSocket:
    def __init__(self, ws_url: str):
        parsed = urllib.parse.urlparse(ws_url)
        self.sock = socket.create_connection((parsed.hostname, parsed.port), timeout=5)
        key = base64.b64encode(os.urandom(16)).decode()
        request = (
            f"GET {parsed.path} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode())
        response = self.sock.recv(4096)
        if b"101" not in response.split(b"\r\n", 1)[0]:
            raise RuntimeError(f"WebSocket handshake failed: {response[:200]!r}")
        self.next_id = 1

    def send(self, obj: dict) -> int:
        msg_id = self.next_id
        self.next_id += 1
        obj = {"id": msg_id, **obj}
        data = json.dumps(obj).encode()
        header = bytearray([0x81])
        length = len(data)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(data))
        self.sock.sendall(header + masked)
        return msg_id

    def recv(self) -> dict | None:
        header = self.sock.recv(2)
        if not header:
            return None
        b1, b2 = header
        length = b2 & 0x7F
        if length == 126:
            length = struct.unpack("!H", self.sock.recv(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self.sock.recv(8))[0]
        if b2 & 0x80:
            mask = self.sock.recv(4)
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(self.sock.recv(length)))
        else:
            chunks = []
            remaining = length
            while remaining:
                chunk = self.sock.recv(remaining)
                chunks.append(chunk)
                remaining -= len(chunk)
            payload = b"".join(chunks)
        if b1 & 0x0F == 8:
            return None
        return json.loads(payload.decode())

    def evaluate(self, expression: str) -> dict:
        msg_id = self.send(
            {
                "method": "Runtime.evaluate",
                "params": {"expression": expression, "returnByValue": True},
            }
        )
        while True:
            message = self.recv()
            if message and message.get("id") == msg_id:
                return message.get("result", {}).get("result", {}).get("value")

    def close(self) -> None:
        self.sock.close()


def main() -> int:
    target = choose_copilot_target()
    print(f"target: {target['url']}")
    cdp = CDPWebSocket(target["webSocketDebuggerUrl"])
    try:
        smart_result = cdp.evaluate(
            """
(() => {
  const smart = document.querySelector('button[aria-label="Smart"]');
  if (!smart) return { clicked: false, reason: 'Smart button not found' };
  smart.click();
  return { clicked: true, label: smart.getAttribute('aria-label') };
})()
"""
        )
        print("smart:", smart_result)
        time.sleep(0.5)
        think_result = cdp.evaluate(
            """
(() => {
  const think = document.querySelector('button[aria-label^="Think deeper"]');
  if (!think) {
    return {
      clicked: false,
      reason: 'Think deeper option not found',
      candidates: [...document.querySelectorAll('button')]
        .map((button) => ({
          label: button.getAttribute('aria-label'),
          title: button.getAttribute('title'),
          testid: button.dataset.testid,
          text: button.textContent.trim(),
          visible: Boolean(button.offsetParent),
        }))
        .filter((item) => String(item.label || item.text || '').includes('Think') || String(item.label || item.text || '').includes('Smart')),
    };
  }
  think.click();
  return {
    clicked: true,
    label: think.getAttribute('aria-label'),
    title: think.getAttribute('title'),
    testid: think.dataset.testid,
  };
})()
"""
        )
        print("think:", think_result)
        time.sleep(0.3)
        verify = cdp.evaluate(
            """
(() => [...document.querySelectorAll('button')]
  .map((button) => ({
    label: button.getAttribute('aria-label'),
    title: button.getAttribute('title'),
    testid: button.dataset.testid,
    text: button.textContent.trim(),
    visible: Boolean(button.offsetParent),
  }))
  .filter((item) => String(item.label || item.text || '').includes('Think') || String(item.label || item.text || '').includes('Smart'))
)()
"""
        )
        print("verify:", verify)
        return 0 if any(item.get("label") == "Think deeper" for item in (verify or [])) else 1
    finally:
        cdp.close()


if __name__ == "__main__":
    sys.exit(main())
