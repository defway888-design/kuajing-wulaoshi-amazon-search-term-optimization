#!/usr/bin/env python3
"""Local, one-run browser bridge for three pre-report filters plus derived site code.

The bridge never calls LingXing or receives its credentials. The running Agent
reads the validated choice file, calls its own authorized MCP tools, and writes
the final offline HTML. This service only transfers the browser selection.
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys

from render_dashboard import InputError, normalize, render, require_dict


ROOT = Path(__file__).resolve().parents[1]


def outside_package(path: Path) -> Path:
    resolved = path.resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise InputError("运行文件必须位于公开 Skill 包外")
    return resolved


def validate_choice(raw: object, payload: dict) -> dict:
    choice = require_dict(raw, "筛选条件")
    if set(choice) != {"date", "site", "country", "store"}:
        raise InputError("筛选提交必须包含日期、国家、店铺及内部站点代码")
    if any(not isinstance(value, str) for value in choice.values()):
        raise InputError("筛选条件类型无效")
    if choice["date"] not in {w["key"] for w in payload["dateWindows"]}:
        raise InputError("统计日期无效")
    sites = {site["code"]: site["country"] for site in payload["sites"]}
    if choice["site"] and choice["site"] not in sites:
        raise InputError("站点无效")
    if choice["country"] != sites.get(choice["site"], ""):
        raise InputError("站点与国家不一致")
    profiles = [p for p in payload["profiles"] if not choice["site"] or p["site"] == choice["site"]]
    if choice["store"]:
        profiles = [p for p in profiles if p["key"] == choice["store"]]
    if not profiles:
        raise InputError("当前条件未命中授权店铺")
    return choice


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="仅含授权店铺和日期定义的 JSON")
    parser.add_argument("--page", required=True, type=Path, help="固定渲染器生成的信息收集页")
    parser.add_argument("--choice", required=True, type=Path, help="Agent 内部读取的选择 JSON")
    parser.add_argument("--final", required=True, type=Path, help="Agent 将写入的离线正式 HTML")
    parser.add_argument("--status-file", required=True, type=Path, help="Agent 可写入错误状态 JSON")
    parser.add_argument("--ready", required=True, type=Path, help="服务启动后写入本地 URL")
    args = parser.parse_args()
    try:
        source, page, choice_path, final_path, status_path, ready_path = [
            outside_package(value) for value in
            (args.input, args.page, args.choice, args.final, args.status_file, args.ready)
        ]
        if len({source, page, choice_path, final_path, status_path, ready_path}) != 6:
            raise InputError("运行文件路径不得相同")
        if choice_path.exists() or final_path.exists() or status_path.exists() or ready_path.exists():
            raise InputError("本次运行输出已存在，请使用新的运行目录")
        raw = require_dict(json.loads(source.read_text(encoding="utf-8")), "授权清单")
        payload = normalize(raw, "selection")
        page_bytes = render(raw, "selection")
        if page.read_bytes() != page_bytes:
            raise InputError("筛选页与固定母版不一致")
        choice_path.parent.mkdir(parents=True, exist_ok=True)

        class Handler(BaseHTTPRequestHandler):
            def ready(self) -> bool:
                if not final_path.is_file() or not status_path.is_file():
                    return False
                try:
                    state = require_dict(json.loads(status_path.read_text(encoding="utf-8")), "状态")
                    return state.get("state") == "ready"
                except (OSError, ValueError, json.JSONDecodeError):
                    return False

            def send_bytes(self, code: int, data: bytes, content_type: str) -> None:
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(data)

            def send_json(self, code: int, value: dict) -> None:
                self.send_bytes(code, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

            def do_GET(self) -> None:
                if self.path == "/":
                    self.send_bytes(200, page_bytes, "text/html; charset=utf-8")
                elif self.path == "/status":
                    if status_path.is_file():
                        try:
                            state = require_dict(json.loads(status_path.read_text(encoding="utf-8")), "状态")
                            if state.get("state") == "ready" and self.ready():
                                self.send_json(200, {"state": "ready"})
                            elif state.get("state") == "ready":
                                self.send_json(200, {"state": "working"})
                            else:
                                self.send_json(200, {"state": "error", "message": str(state.get("message") or "生成失败")})
                        except (OSError, ValueError, json.JSONDecodeError):
                            self.send_json(200, {"state": "working"})
                    else:
                        self.send_json(200, {"state": "working" if choice_path.exists() else "waiting"})
                elif self.path == "/final" and self.ready():
                    self.send_bytes(200, final_path.read_bytes(), "text/html; charset=utf-8")
                else:
                    self.send_json(404, {"message": "未找到页面"})

            def do_POST(self) -> None:
                origin = self.headers.get("Origin", "")
                expected = "http://127.0.0.1:" + str(self.server.server_port)
                if self.path != "/run" or origin != expected:
                    self.send_json(403, {"message": "请求来源无效"})
                    return
                if choice_path.exists():
                    self.send_json(409, {"message": "本次运行已提交筛选条件"})
                    return
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    self.send_json(415, {"message": "仅接受 JSON 筛选条件"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 1 <= length <= 4096:
                        raise InputError("筛选条件大小无效")
                    request = json.loads(self.rfile.read(length))
                    validated = validate_choice(request, payload)
                    pending = choice_path.with_suffix(choice_path.suffix + ".pending")
                    pending.write_text(json.dumps(validated, ensure_ascii=False), encoding="utf-8")
                    os.replace(pending, choice_path)
                    self.send_json(202, {"state": "working"})
                except (InputError, ValueError, json.JSONDecodeError) as error:
                    self.send_json(400, {"message": str(error)})

            def log_message(self, format: str, *args: object) -> None:
                return

        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            url = "http://127.0.0.1:" + str(server.server_port) + "/"
            ready_path.parent.mkdir(parents=True, exist_ok=True)
            ready_path.write_text(url, encoding="utf-8")
            print(url, flush=True)
            server.serve_forever(poll_interval=0.5)
        return 0
    except (InputError, OSError, json.JSONDecodeError, UnicodeError) as error:
        print("STOP: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
