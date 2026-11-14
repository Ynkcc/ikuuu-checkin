#!/usr/bin/env python3
"""向 @iKuuuu_VPN_bot 发送 /checkin 并记录机器人回复。

首次使用: 先填好 config.json, 再在终端手动运行一次完成登录:
    .venv/bin/python checkin.py --login
登录成功会生成 session.session 文件, 之后 systemd 定时任务免交互运行。
"""
import asyncio
import json
import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from telethon import TelegramClient

BASE = Path(__file__).resolve().parent
LOG_DIR = BASE / "logs"

logger = logging.getLogger("ikuuu")
logger.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")
_stream = logging.StreamHandler()
_stream.setFormatter(_fmt)
_file = RotatingFileHandler(LOG_DIR / "ikuuu.log", maxBytes=1024 * 1024,
                            backupCount=3, encoding="utf-8")
_file.setFormatter(_fmt)
logger.addHandler(_stream)
logger.addHandler(_file)


def load_config():
    cfg = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
    if not cfg.get("api_id") or not cfg.get("api_hash"):
        logger.error("请先在 config.json 中填写 api_id / api_hash (https://my.telegram.org 获取)")
        sys.exit(1)
    return cfg


async def run(client, cfg):
    bot = cfg["bot"]
    command = cfg.get("command", "/checkin")
    sent = await client.send_message(bot, command)
    logger.info(f"已发送 {command} 给 @{bot}")

    # 等待机器人回复 (最多 90 秒)
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        await asyncio.sleep(3)
        msgs = await client.get_messages(bot, limit=5)
        reply = next(
            (m for m in msgs if not m.out and m.date and m.date > sent.date), None)
        if reply:
            text = (reply.message or "").replace("\n", " | ")[:300]
            logger.info(f"机器人回复: {text}")
            return
    logger.warning("90 秒内未收到机器人回复")


async def main():
    cfg = load_config()
    login_mode = "--login" in sys.argv
    session_file = BASE / "session.session"

    proxy = None
    pcfg = cfg.get("proxy") or {}
    if pcfg.get("enabled"):
        proxy = (pcfg.get("type", "socks5"), pcfg.get("host", "127.0.0.1"),
                 int(pcfg.get("port", 7890)))

    client = TelegramClient(str(BASE / "session"), cfg["api_id"], cfg["api_hash"],
                            proxy=proxy)
    await client.connect()
    if not await client.is_user_authorized():
        if not login_mode:
            await client.disconnect()
            logger.error("尚未登录 Telegram。请在终端手动运行一次: "
                         ".venv/bin/python checkin.py --login")
            sys.exit(1)
        # 交互式登录: 输入手机号验证码
        await client.start(phone=cfg["phone"])
        me = await client.get_me()
        logger.info(f"登录成功: {me.first_name} (id={me.id})")
    me = await client.get_me()
    logger.info(f"以 {me.first_name} (id={me.id}) 身份运行签到")
    try:
        await run(client, cfg)
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
