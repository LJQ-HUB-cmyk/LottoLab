"""Prepare a private cloud configuration without printing or replacing credentials."""

import argparse
import json
import secrets
from pathlib import Path

from dotenv import dotenv_values
from lottolab.cloud import postgres_url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate syntax without connecting or writing")
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / ".env.cloud.local"
    if not args.check:
        try:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(
                    "# Private cloud configuration. Never commit or share this file.\n"
                    "# Paste the Neon pooled PostgreSQL URL after the equals sign.\n"
                    "LOTTOLAB_DATABASE_URL=\n"
                    f"LOTTOLAB_ADMIN_TOKEN={secrets.token_urlsafe(36)}\n"
                    "LOTTOLAB_JOB_TIMEOUT_SECONDS=240\n"
                )
            print("已生成 .env.cloud.local 和随机管理令牌；请填写数据库连接，令牌不会输出。")
        except FileExistsError:
            print("已有 .env.cloud.local，完整保留，未改动任何配置。")
        return
    if not path.is_file():
        raise SystemExit("缺少 .env.cloud.local，请先运行本脚本生成配置。")
    values = dotenv_values(path)
    try:
        postgres_url(values.get("LOTTOLAB_DATABASE_URL") or "")
        if len(values.get("LOTTOLAB_ADMIN_TOKEN") or "") < 32:
            raise ValueError("需要至少 32 字符的随机管理员令牌")
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    print(json.dumps({"status": "SYNTAX_PASS", "network_checked": False, "credentials_printed": False}))


if __name__ == "__main__":
    main()
