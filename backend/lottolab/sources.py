"""Fixed public-source adapters. No arbitrary URL fetching."""

import json
import re
import time
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from .domain import Lottery

CWL_URL = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
TC_URL = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"


@dataclass
class SourceBatch:
    source: str
    url: str
    raw: bytes
    records: list[dict]
    reported_total: int | None = None


def money(value) -> str | None:
    text = str(value if value is not None else "").strip().replace(",", "")
    return text if re.fullmatch(r"\d+(\.\d{1,2})?", text) else None


def parse_cwl(payload: dict) -> list[dict]:
    if payload.get("state") != 0 or not isinstance(payload.get("result"), list):
        raise ValueError("中国福彩返回了无法识别的数据结构")
    rows: list[dict] = []
    for item in payload["result"]:
        try:
            rows.append(
                {
                    "issue": str(item["code"]),
                    "draw_date": str(item["date"])[:10],
                    "main_numbers": [int(v) for v in item["red"].split(",")],
                    "special_numbers": [int(item["blue"])],
                    "sales": money(item.get("sales")),
                    "pool_amount": money(item.get("poolmoney")),
                    "prizes": {
                        str(p["type"]): money(p["typemoney"])
                        for p in item.get("prizegrades", [])
                        if money(p.get("typemoney")) is not None and int(p["type"]) <= 6
                    },
                }
            )
        except (KeyError, ValueError, TypeError) as exc:
            rows.append(
                {"issue": str(item.get("code", "")), "_parse_error": f"源字段不完整：{exc}", "raw": item}
            )
    return rows


def parse_500(html: str, lottery: Lottery) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    main_count, special_count = (6, 1) if lottery == "ssq" else (5, 2)
    for tr in soup.select("#tdata tr"):
        cells = [td.get_text(" ", strip=True).replace("\xa0", " ").strip() for td in tr.select("td")]
        if not cells or not re.fullmatch(r"\d{5,7}", cells[0]):
            continue
        try:
            date_cell = next(v for v in reversed(cells) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v))
            issue = "20" + cells[0] if len(cells[0]) == 5 else cells[0]
            rows.append(
                {
                    "issue": issue,
                    "draw_date": date_cell,
                    "main_numbers": [int(v) for v in cells[1 : 1 + main_count]],
                    "special_numbers": [
                        int(v) for v in cells[1 + main_count : 1 + main_count + special_count]
                    ],
                }
            )
        except (ValueError, StopIteration) as exc:
            rows.append(
                {"issue": cells[0], "_parse_error": f"备用源行解析失败：{exc}", "raw": {"cells": cells}}
            )
    if not rows:
        raise ValueError("备用数据页没有可识别的开奖记录")
    return rows


def parse_sporttery(payload: dict) -> list[dict]:
    value = payload.get("value", {})
    items = value.get("list")
    if not isinstance(items, list):
        raise ValueError("中国体彩返回了无法识别的数据结构")
    rows: list[dict] = []
    for item in items:
        try:
            numbers = [int(v) for v in re.split(r"[,\s]+", item["lotteryDrawResult"].strip())]
            issue = str(item["lotteryDrawNum"])
            issue = "20" + issue if len(issue) == 5 else issue
            rows.append(
                {
                    "issue": issue,
                    "draw_date": item["lotteryDrawTime"][:10],
                    "main_numbers": numbers[:5],
                    "special_numbers": numbers[5:7],
                    "sales": money(item.get("totalSaleAmount")),
                    "pool_amount": money(item.get("poolBalanceAfterdraw")),
                }
            )
        except (KeyError, ValueError, TypeError) as exc:
            rows.append({"issue": str(item.get("lotteryDrawNum", "")), "_parse_error": str(exc), "raw": item})
    return rows


def request(client: httpx.Client, url: str, params: dict) -> httpx.Response:
    last_error = None
    for attempt in range(3):
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            if len(response.content) > 12 * 1024 * 1024:
                raise ValueError("数据源响应超过大小限制")
            return response
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
            last_error = exc
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (401, 403, 404):
                break
            if attempt < 2:
                time.sleep(0.5 * 2**attempt)
    raise RuntimeError("公开数据源请求失败，请稍后重试或导入 CSV") from last_error


def fetch_source(lottery: Lottery, count: int, timeout: float = 20) -> tuple[list[SourceBatch], list[str]]:
    errors: list[str] = []
    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        headers={
            "User-Agent": "LottoLab/0.1 (public historical data research)",
            "Referer": "https://www.cwl.gov.cn/ygkj/wqkjgg/ssq/",
        },
    ) as client:
        batches = []
        try:
            remaining = count
            page = 1
            while remaining > 0:
                size = min(1000, count) if lottery == "ssq" else min(100, count)
                url = CWL_URL if lottery == "ssq" else TC_URL
                params = (
                    {"name": "ssq", "pageNo": page, "pageSize": size, "systemType": "PC"}
                    if lottery == "ssq"
                    else {
                        "gameNo": "85",
                        "provinceId": "0",
                        "pageSize": size,
                        "pageNo": page,
                        "isVerify": "1",
                    }
                )
                response = request(client, url, params)
                payload = response.json()
                records = parse_cwl(payload) if lottery == "ssq" else parse_sporttery(payload)
                if not records:
                    break
                batches.append(
                    SourceBatch(
                        "中国福彩" if lottery == "ssq" else "中国体彩",
                        str(response.url),
                        response.content,
                        records[:remaining],
                        payload.get("total"),
                    )
                )
                remaining -= len(records)
                if len(records) < size:
                    break
                page += 1
                if remaining > 0:
                    time.sleep(0.8)
            if batches:
                return batches, errors
            raise ValueError("官方源返回空数据")
        except (RuntimeError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            errors.append("官方数据源暂不可用，已尝试备用来源；可通过导入报告查看实际来源。")
        url = f"https://datachart.500.com/{lottery}/history/newinc/history.php"
        response = request(client, url, {"limit": count})
        html = response.content.decode("utf-8", errors="replace")
        records = parse_500(html, lottery)[:count]
        return [SourceBatch("500 公开数据（备用）", str(response.url), response.content, records)], errors
