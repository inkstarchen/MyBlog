from __future__ import annotations

import argparse
import functools
import socket
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from build import ROOT, build


class QuietStaticHandler(SimpleHTTPRequestHandler):
    """Serve the generated site with concise request logging."""

    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")


def local_address(host: str, port: int) -> str:
    display_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    return f"http://{display_host}:{port}/"


def lan_address(port: int) -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            return f"http://{probe.getsockname()[0]}:{port}/"
    except OSError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="在本机部署并预览认知空间")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，默认仅本机可访问")
    parser.add_argument("--port", type=int, default=8000, help="访问端口，默认 8000")
    parser.add_argument("--no-build", action="store_true", help="跳过生成，直接使用现有 dist")
    parser.add_argument("--open", action="store_true", help="启动后自动打开浏览器")
    args = parser.parse_args()

    output_dir = ROOT / "dist"
    if not args.no_build:
        output_dir = build(ROOT / "site.json")
    elif not (output_dir / "index.html").exists():
        parser.error("dist/index.html 不存在，请先移除 --no-build 或运行 python build.py")

    handler = functools.partial(QuietStaticHandler, directory=str(output_dir))
    try:
        server = ThreadingHTTPServer((args.host, args.port), handler)
    except OSError as error:
        raise SystemExit(f"无法启动：{args.host}:{args.port} 不可用（{error}）") from error

    address = local_address(args.host, args.port)
    print("\n认知空间已在本地运行：")
    print(f"  {address}")
    if args.host in {"0.0.0.0", "::"}:
        network_address = lan_address(args.port)
        if network_address:
            print(f"局域网设备可访问：\n  {network_address}")
        print("注意：当前已允许同一网络中的其他设备访问。")
    print("按 Ctrl+C 停止。\n", flush=True)

    if args.open:
        threading.Timer(0.4, webbrowser.open, args=(address,)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n本地站点已停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
