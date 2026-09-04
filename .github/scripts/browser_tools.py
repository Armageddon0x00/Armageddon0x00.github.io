#!/usr/bin/env python3
"""Exact-viewport Chromium audits and screenshots for catakan.net."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "site-config.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def find_chromium() -> str:
    for candidate in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        executable = shutil.which(candidate)
        if executable:
            return executable
    raise RuntimeError("Chromium/Chrome executable not found")


def timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


class WebSocketConnection:
    """Minimal RFC 6455 client sufficient for the Chrome DevTools Protocol."""

    def __init__(self, url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme != "ws" or not parsed.hostname or not parsed.port:
            raise RuntimeError(f"unsupported DevTools WebSocket URL: {url}")
        self.socket = socket.create_connection((parsed.hostname, parsed.port), timeout=10)
        self.socket.settimeout(1)
        self.buffer = bytearray()
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode("ascii")
        self.socket.sendall(request)
        response = self._read_until(b"\r\n\r\n")
        status_line = response.split(b"\r\n", 1)[0]
        if b" 101 " not in status_line:
            raise RuntimeError(f"DevTools WebSocket handshake failed: {status_line.decode(errors='replace')}")
        expected_accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        headers = response.decode("latin-1").lower()
        if f"sec-websocket-accept: {expected_accept.lower()}" not in headers:
            raise RuntimeError("DevTools WebSocket handshake returned an invalid accept key")

    def _read_until(self, delimiter: bytes) -> bytes:
        while delimiter not in self.buffer:
            chunk = self.socket.recv(65536)
            if not chunk:
                raise RuntimeError("DevTools WebSocket closed during handshake")
            self.buffer.extend(chunk)
        end = self.buffer.index(delimiter) + len(delimiter)
        result = bytes(self.buffer[:end])
        del self.buffer[:end]
        return result

    def _read_exact(self, length: int) -> bytes:
        while len(self.buffer) < length:
            chunk = self.socket.recv(max(65536, length - len(self.buffer)))
            if not chunk:
                raise RuntimeError("DevTools WebSocket closed unexpectedly")
            self.buffer.extend(chunk)
        result = bytes(self.buffer[:length])
        del self.buffer[:length]
        return result

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        mask = os.urandom(4)
        length = len(payload)
        header = bytearray([0x80 | opcode])
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack(">H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack(">Q", length))
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.socket.sendall(bytes(header) + mask + masked)

    def send_json(self, payload: dict) -> None:
        self._send_frame(0x1, json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    def receive_json(self) -> dict:
        fragments = bytearray()
        while True:
            first, second = self._read_exact(2)
            final = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read_exact(8))[0]
            mask = self._read_exact(4) if masked else b""
            payload = self._read_exact(length)
            if masked:
                payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
            if opcode == 0x8:
                raise RuntimeError("DevTools WebSocket closed")
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode in {0x1, 0x0}:
                fragments.extend(payload)
                if final:
                    return json.loads(fragments.decode("utf-8"))

    def close(self) -> None:
        try:
            self._send_frame(0x8, b"")
        except OSError:
            pass
        self.socket.close()


class DevToolsClient:
    def __init__(self, websocket_url: str) -> None:
        self.connection = WebSocketConnection(websocket_url)
        self.next_id = 1
        self.events: list[dict] = []

    def call(self, method: str, params: dict | None = None, timeout: float = 20) -> dict:
        call_id = self.next_id
        self.next_id += 1
        message: dict = {"id": call_id, "method": method}
        if params is not None:
            message["params"] = params
        self.connection.send_json(message)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                response = self.connection.receive_json()
            except TimeoutError:
                continue
            if response.get("id") == call_id:
                if "error" in response:
                    raise RuntimeError(f"DevTools {method} failed: {response['error']}")
                return response.get("result", {})
            self.events.append(response)
        raise RuntimeError(f"DevTools command timed out: {method}")

    def wait_event(self, method: str, timeout: float = 20) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for index, event in enumerate(self.events):
                if event.get("method") == method:
                    return self.events.pop(index).get("params", {})
            try:
                event = self.connection.receive_json()
            except TimeoutError:
                continue
            if event.get("method") == method:
                return event.get("params", {})
            self.events.append(event)
        raise RuntimeError(f"DevTools event timed out: {method}")

    def clear_events(self) -> None:
        self.events.clear()

    def close(self) -> None:
        self.connection.close()


ERROR_PROBE = r"""
window.__catakanAuditErrors = [];
(function () {
  const allowed = ["https://static.cloudflareinsights.com/", "https://cloudflareinsights.com/"];
  const record = (kind, detail) => {
    const value = String(detail || "unknown");
    if (allowed.some((prefix) => value.startsWith(prefix))) return;
    window.__catakanAuditErrors.push({ kind, detail: value });
  };
  window.addEventListener("error", (event) => {
    const target = event.target;
    if (target && target !== window) {
      record("resource", target.currentSrc || target.src || target.href || target.tagName);
      return;
    }
    record("javascript", event.message || event.error);
  }, true);
  window.addEventListener("unhandledrejection", (event) => record("promise", event.reason));
  const originalError = console.error.bind(console);
  console.error = (...args) => {
    record("console", args.map(String).join(" "));
    originalError(...args);
  };
})();
"""


def audit_expression(route: dict) -> str:
    expected = [{"name": item["name"], "selector": item["selector"]} for item in route["snap_targets"]]
    forbidden = route.get("must_not_snap", [])
    return f"""
(() => {{
  const expected = {json.dumps(expected)};
  const forbidden = {json.dumps(forbidden)};
  const expectedElements = expected.map((item) => document.querySelector(item.selector));
  const describe = (element) => {{
    if (!element) return "missing";
    if (element.id) return `#${{element.id}}`;
    const classes = Array.from(element.classList || []);
    return classes.length
      ? `${{element.tagName.toLowerCase()}}.${{classes.join(".")}}`
      : element.tagName.toLowerCase();
  }};
  const snapTargets = expected.map((item, index) => {{
    const element = expectedElements[index];
    if (!element) return {{ ...item, exists: false }};
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return {{
      ...item,
      exists: true,
      align: style.scrollSnapAlign,
      stop: style.scrollSnapStop,
      offsetTop: Math.round(element.offsetTop),
      height: Math.round(rect.height),
      scrollHeight: element.scrollHeight,
    }};
  }});
  const actualSnaps = Array.from(document.querySelectorAll("body *"))
    .filter((element) => getComputedStyle(element).scrollSnapAlign !== "none")
    .map((element) => ({{
      element: describe(element),
      align: getComputedStyle(element).scrollSnapAlign,
      stop: getComputedStyle(element).scrollSnapStop,
      expected: expectedElements.includes(element),
    }}));
  const forbiddenSnaps = forbidden.map((selector) => {{
    const element = document.querySelector(selector);
    return {{
      selector,
      exists: Boolean(element),
      align: element ? getComputedStyle(element).scrollSnapAlign : "missing",
    }};
  }});
  const brokenImages = Array.from(document.images)
    .filter((image) => (image.currentSrc || image.getAttribute("src")) && image.complete && image.naturalWidth === 0)
    .map((image) => image.currentSrc || image.src || image.alt || "unnamed image");
  const longAnimations = document.getAnimations()
    .filter((animation) => {{
      const timing = animation.effect && animation.effect.getComputedTiming();
      return animation.playState === "running" && timing && Number(timing.duration) > 20;
    }})
    .map((animation) => {{
      const target = animation.effect && animation.effect.target;
      const timing = animation.effect && animation.effect.getComputedTiming();
      return {{ target: describe(target), duration: Number(timing.duration) }};
    }});
  const root = document.documentElement;
  const body = document.body;
  return {{
    url: location.pathname,
    viewport: {{ width: innerWidth, height: innerHeight }},
    scrollSnapType: getComputedStyle(root).scrollSnapType,
    documentWidth: Math.max(root.scrollWidth, body.scrollWidth),
    horizontalOverflow: Math.max(0, Math.max(root.scrollWidth, body.scrollWidth) - root.clientWidth),
    snapTargets,
    actualSnaps,
    forbiddenSnaps,
    brokenImages,
    errors: window.__catakanAuditErrors || [],
    longAnimations,
    reducedMotion: matchMedia("(prefers-reduced-motion: reduce)").matches,
  }};
}})()
"""


class ChromiumSession:
    def __init__(self) -> None:
        self.profile = tempfile.TemporaryDirectory(
            prefix="catakan-browser-profile-",
            ignore_cleanup_errors=True,
        )
        executable = find_chromium()
        self.process = subprocess.Popen(
            [
                executable,
                "--headless=new",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-background-networking",
                "--disable-component-update",
                "--disable-default-apps",
                "--disable-features=MediaRouter,Translate",
                "--disable-sync",
                "--hide-scrollbars",
                "--metrics-recording-only",
                "--no-first-run",
                "--no-default-browser-check",
                "--remote-allow-origins=*",
                "--remote-debugging-port=0",
                f"--user-data-dir={self.profile.name}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        active_port = Path(self.profile.name) / "DevToolsActivePort"
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not active_port.exists():
            if self.process.poll() is not None:
                raise RuntimeError("Chromium exited before opening DevTools")
            time.sleep(0.05)
        if not active_port.exists():
            raise RuntimeError("Chromium did not open DevTools within 15 seconds")
        port = active_port.read_text(encoding="utf-8").splitlines()[0]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
            targets = json.load(response)
        page = next((target for target in targets if target.get("type") == "page"), None)
        if not page:
            raise RuntimeError("Chromium exposed no page target")
        self.client = DevToolsClient(page["webSocketDebuggerUrl"])
        for domain in ("Page", "Runtime", "Log", "Network"):
            self.client.call(f"{domain}.enable")
        self.client.call("Network.setBlockedURLs", {
            "urls": ["*static.cloudflareinsights.com*", "*cloudflareinsights.com*"],
        })
        self.client.call("Page.addScriptToEvaluateOnNewDocument", {"source": ERROR_PROBE})

    def evaluate(self, expression: str, await_promise: bool = False) -> object:
        response = self.client.call("Runtime.evaluate", {
            "expression": expression,
            "awaitPromise": await_promise,
            "returnByValue": True,
        })
        if "exceptionDetails" in response:
            details = response["exceptionDetails"]
            raise RuntimeError(f"browser evaluation failed: {details.get('text', details)}")
        return response.get("result", {}).get("value")

    def navigate(self, url: str, viewport: dict, reduced: bool = False) -> None:
        self.client.call("Emulation.setDeviceMetricsOverride", {
            "width": viewport["width"],
            "height": viewport["height"],
            "deviceScaleFactor": 1,
            "mobile": viewport["name"] == "mobile",
            "screenWidth": viewport["width"],
            "screenHeight": viewport["height"],
        })
        self.client.call("Emulation.setEmulatedMedia", {
            "features": [{
                "name": "prefers-reduced-motion",
                "value": "reduce" if reduced else "no-preference",
            }],
        })
        self.client.clear_events()
        self.client.call("Page.navigate", {"url": url})
        self.client.wait_event("Page.loadEventFired", timeout=25)
        self.evaluate("new Promise((resolve) => setTimeout(resolve, 700))", await_promise=True)

    def screenshot(self) -> bytes:
        response = self.client.call("Page.captureScreenshot", {
            "format": "png",
            "fromSurface": True,
            "captureBeyondViewport": False,
        }, timeout=30)
        return base64.b64decode(response["data"])

    def close(self) -> None:
        try:
            self.client.close()
        finally:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
            self.profile.cleanup()

    def __enter__(self) -> "ChromiumSession":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()


def audit(config: dict, base_url: str) -> int:
    report_path = Path("/tmp") / f"catakan-audit-{timestamp()}.json"
    results: list[dict] = []
    errors: list[str] = []
    warnings: list[str] = []
    print("BROWSER AUDIT", flush=True)

    with ChromiumSession() as browser:
        for route in config["routes"]:
            for viewport in config["viewports"]:
                label = f"{route['name']} / {viewport['name']}"
                try:
                    browser.navigate(base_url.rstrip("/") + route["path"], viewport)
                    result = browser.evaluate(audit_expression(route))
                    if not isinstance(result, dict):
                        raise RuntimeError("browser returned no audit object")
                    result.update({"route": route["name"], "viewportName": viewport["name"], "mode": "normal"})
                    results.append(result)
                except Exception as error:
                    errors.append(f"{label}: {error}")
                    continue

                measured = result["viewport"]
                if (measured["width"], measured["height"]) != (viewport["width"], viewport["height"]):
                    errors.append(
                        f"{label}: measured {measured['width']}x{measured['height']}, "
                        f"expected {viewport['width']}x{viewport['height']}"
                    )
                if "mandatory" not in result["scrollSnapType"]:
                    errors.append(f"{label}: root scroll-snap type is {result['scrollSnapType']!r}, expected mandatory")
                if result["horizontalOverflow"] > 1:
                    errors.append(f"{label}: document overflows horizontally by {result['horizontalOverflow']}px")
                if result["errors"]:
                    errors.append(f"{label}: browser errors: {json.dumps(result['errors'], ensure_ascii=False)}")
                if result["brokenImages"]:
                    errors.append(f"{label}: broken images: {', '.join(result['brokenImages'])}")
                for target in result["snapTargets"]:
                    if not target.get("exists"):
                        errors.append(f"{label}: missing snap target {target['selector']}")
                        continue
                    if target["align"] == "none":
                        errors.append(f"{label}: {target['selector']} is not a snap target")
                    if target["height"] > measured["height"] * 1.12:
                        warnings.append(
                            f"{label}: {target['name']} is {target['height']}px tall in a "
                            f"{measured['height']}px viewport"
                        )
                unexpected = [item["element"] for item in result["actualSnaps"] if not item["expected"]]
                if unexpected:
                    errors.append(f"{label}: unexpected snap targets: {', '.join(unexpected)}")
                active_forbidden = [
                    item["selector"] for item in result["forbiddenSnaps"]
                    if item["exists"] and item["align"] != "none"
                ]
                if active_forbidden:
                    errors.append(f"{label}: forbidden nested snap targets: {', '.join(active_forbidden)}")
                positions = ", ".join(
                    f"{item['name']}@{item.get('offsetTop', 'missing')}" for item in result["snapTargets"]
                )
                print(f"PASS  {label}: {positions}", flush=True)

            desktop = next(item for item in config["viewports"] if item["name"] == "desktop")
            label = f"{route['name']} / desktop / reduced-motion"
            try:
                browser.navigate(base_url.rstrip("/") + route["path"], desktop, reduced=True)
                reduced_result = browser.evaluate(audit_expression(route))
                if not isinstance(reduced_result, dict):
                    raise RuntimeError("browser returned no reduced-motion audit object")
                reduced_result.update({"route": route["name"], "viewportName": "desktop", "mode": "reduced"})
                results.append(reduced_result)
                if reduced_result["scrollSnapType"] != "none":
                    errors.append(f"{label}: scroll snapping remains enabled ({reduced_result['scrollSnapType']})")
                if reduced_result["longAnimations"]:
                    errors.append(
                        f"{label}: long-running animations remain: "
                        f"{json.dumps(reduced_result['longAnimations'], ensure_ascii=False)}"
                    )
                if reduced_result["errors"]:
                    errors.append(f"{label}: browser errors: {json.dumps(reduced_result['errors'], ensure_ascii=False)}")
                print(f"PASS  {label}", flush=True)
            except Exception as error:
                errors.append(f"{label}: {error}")

    report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for warning in warnings:
        print(f"WARN  {warning}")
    for error in errors:
        print(f"FAIL  {error}", file=sys.stderr)
    print(f"REPORT {report_path}")
    if errors:
        print(f"FAILED with {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"PASSED with {len(warnings)} warning(s)")
    return 0


def png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("Chromium did not return a valid PNG")
    return struct.unpack(">II", data[16:24])


def capture(config: dict, base_url: str, output: str | None) -> int:
    output_dir = Path(output).resolve() if output else Path("/tmp") / f"catakan-preview-{timestamp()}"
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest: list[dict] = []
    errors: list[str] = []
    print("VIEWPORT CAPTURE", flush=True)

    with ChromiumSession() as browser:
        for route in config["routes"]:
            for viewport in config["viewports"]:
                try:
                    browser.navigate(base_url.rstrip("/") + route["path"], viewport)
                except Exception as error:
                    errors.append(f"{route['name']} / {viewport['name']}: navigation failed: {error}")
                    continue
                for target in route["snap_targets"]:
                    filename = f"{route['name']}--{target['name']}--{viewport['name']}.png"
                    destination = output_dir / filename
                    try:
                        found = browser.evaluate(
                            f"""
(() => {{
  const target = document.querySelector({json.dumps(target['selector'])});
  if (!target) return false;
  target.scrollIntoView({{ behavior: "instant", block: "start" }});
  return true;
}})()
"""
                        )
                        if not found:
                            raise RuntimeError(f"missing selector {target['selector']}")
                        browser.evaluate("new Promise((resolve) => setTimeout(resolve, 900))", await_promise=True)
                        png = browser.screenshot()
                        actual_width, actual_height = png_dimensions(png)
                        if (actual_width, actual_height) != (viewport["width"], viewport["height"]):
                            raise RuntimeError(
                                f"expected {viewport['width']}x{viewport['height']}, "
                                f"got {actual_width}x{actual_height}"
                            )
                        destination.write_bytes(png)
                    except Exception as error:
                        errors.append(f"{filename}: {error}")
                        continue
                    url = f"{base_url.rstrip('/')}{route['path']}#{target['fragment']}"
                    manifest.append({
                        "route": route["name"],
                        "section": target["name"],
                        "viewport": viewport["name"],
                        "dimensions": f"{actual_width}x{actual_height}",
                        "url": url,
                        "file": str(destination),
                    })
                    print(f"PASS  {filename}", flush=True)

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for error in errors:
        print(f"FAIL  {error}", file=sys.stderr)
    print(f"OUTPUT {output_dir}")
    print(f"MANIFEST {manifest_path}")
    if errors:
        print(f"FAILED with {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"PASSED: {len(manifest)} screenshots")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit_parser = subparsers.add_parser("audit", help="run exact-viewport layout and motion audits")
    audit_parser.add_argument("--base-url", default="http://127.0.0.1:4173")
    capture_parser = subparsers.add_parser("capture", help="capture every snap viewport")
    capture_parser.add_argument("--base-url", default="http://127.0.0.1:4173")
    capture_parser.add_argument("--output", help="output directory; defaults to /tmp/catakan-preview-TIMESTAMP")
    args = parser.parse_args()
    config = load_config()
    if args.command == "audit":
        return audit(config, args.base_url)
    return capture(config, args.base_url, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
