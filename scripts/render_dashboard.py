#!/usr/bin/env python3
"""Render the fixed Wu Lao Shi offline search-term dashboard.

Only verified payloads and the bundled logo are injected into one HTML shell.
Python standard library only; no MCP calls or operating-system-specific paths.
"""

from __future__ import annotations

import argparse
import base64
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "assets" / "dashboard_template.html"
LOGO = ROOT / "assets" / "logo.jpg"
WINDOWS = ("7天", "14天", "本月", "上月")
# Bumped only when the reviewed canonical template intentionally changes.
TEMPLATE_SHA256 = "be70cffa80330a33466d52aac3a02b48244af21fbe77f785a7d252758c8793af"


class InputError(ValueError):
    pass


def require_dict(value: object, where: str) -> dict:
    if not isinstance(value, dict):
        raise InputError(f"{where} 必须为对象")
    return value


def require_list(value: object, where: str) -> list:
    if not isinstance(value, list):
        raise InputError(f"{where} 必须为数组")
    return value


def nonempty(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{where} 必须为非空文本")
    return value.strip()


def reference(value: object, where: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).strip():
        raise InputError(f"{where} 缺少身份引用")
    return str(value).strip()


def number(value: object, where: str, maximum: Optional[float] = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{where} 必须为数字")
    result = float(value)
    if not math.isfinite(result) or result < 0 or result > 9007199254740991 or (maximum is not None and result > maximum):
        raise InputError(f"{where} 超出合法范围")
    return result


def optional_number(value: object, where: str, maximum: Optional[float] = None) -> Optional[float]:
    return None if value is None else number(value, where, maximum)


def date_string(value: object, where: str) -> str:
    text = nonempty(value, where)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise InputError(f"{where} 格式应为 YYYY-MM-DD")
    try:
        date.fromisoformat(text)
    except ValueError as error:
        raise InputError(f"{where} 不是有效自然日") from error
    return text


def normalize(raw: dict) -> dict:
    windows_in = require_list(raw.get("dateWindows"), "dateWindows")
    if [w.get("key") for w in windows_in if isinstance(w, dict)] != list(WINDOWS):
        raise InputError("dateWindows 必须依次包含 7天、14天、本月、上月")
    windows = []
    for index, value in enumerate(windows_in):
        w = require_dict(value, f"dateWindows[{index}]")
        start = date_string(w.get("start"), f"dateWindows[{index}].start")
        end = date_string(w.get("end"), f"dateWindows[{index}].end")
        if start > end:
            raise InputError("日期窗口起日晚于止日")
        windows.append({"key": w["key"], "start": start, "end": end})
    days = [(date.fromisoformat(w["start"]), date.fromisoformat(w["end"])) for w in windows]
    today = days[0][1]
    if (days[0][0] != today - timedelta(days=6) or
            days[1] != (today - timedelta(days=13), today) or
            days[2] != (today.replace(day=1), today) or
            days[3][1] != today.replace(day=1) - timedelta(days=1) or
            days[3][0] != days[3][1].replace(day=1)):
        raise InputError("四个日期窗口的自然日范围不一致")

    timezone = nonempty(raw.get("timezone"), "timezone")
    initial = raw.get("initialWindow", "上月")
    if initial not in WINDOWS:
        raise InputError("initialWindow 必须是四个固定窗口之一")

    profiles_in = require_list(raw.get("profiles"), "profiles")
    if not profiles_in:
        raise InputError("profiles 为空")
    profiles = []
    profile_by_ref = {}
    site_by_code = {}
    for index, value in enumerate(profiles_in):
        p = require_dict(value, f"profiles[{index}]")
        ref = reference(p.get("profileRef"), f"profiles[{index}].profileRef")
        if ref in profile_by_ref:
            raise InputError("重复的 profileRef")
        site = nonempty(p.get("site"), f"profiles[{index}].site").upper()
        country = nonempty(p.get("country"), f"profiles[{index}].country")
        currency = nonempty(p.get("currency"), f"profiles[{index}].currency")
        shop = nonempty(p.get("shop"), f"profiles[{index}].shop")
        if site in site_by_code and site_by_code[site] != (country, currency):
            raise InputError(f"站点 {site} 的国家或币种信息冲突")
        site_by_code[site] = (country, currency)
        display = {"key": f"p{index + 1}", "site": site, "country": country, "currency": currency, "shop": shop}
        profiles.append(display)
        profile_by_ref[ref] = display

    sites = [{"code": code, "country": pair[0], "currency": pair[1]} for code, pair in sorted(site_by_code.items())]
    if len({site["country"] for site in sites}) != len(sites):
        raise InputError("国家名称与站点代码无法唯一对应，不能只用国家筛选")
    selected_window = raw.get("selectedWindow")
    if selected_window not in WINDOWS:
        raise InputError("正式看板必须指定第一阶段确认的统计日期")
    scope = require_dict(raw.get("selectedScope"), "selectedScope")
    if set(scope) != {"date", "site", "country", "profileRef"} or scope["date"] != selected_window:
        raise InputError("正式看板的选择范围与统计日期不一致")
    if not isinstance(scope["site"], str) or not isinstance(scope["country"], str):
        raise InputError("选择范围的站点或国家无效")
    site_country = {s["code"]: s["country"] for s in sites}
    if scope["site"] and scope["site"] not in site_country:
        raise InputError("选择范围的站点无效")
    if scope["country"] != site_country.get(scope["site"], ""):
        raise InputError("选择范围的站点与国家不一致")
    if scope["site"] and any(p["site"] != scope["site"] for p in profiles):
        raise InputError("正式报告包含所选站点之外的店铺")
    selected_ref = scope["profileRef"]
    if selected_ref is not None:
        selected_ref = reference(selected_ref, "selectedScope.profileRef")
        if selected_ref not in profile_by_ref or len(profiles) != 1:
            raise InputError("正式报告的店铺与用户选择不一致")
    coverage_in = require_list(raw.get("coverage"), "coverage")
    coverage = {}
    for index, value in enumerate(coverage_in):
        item = require_dict(value, f"coverage[{index}]")
        ref = reference(item.get("profileRef"), f"coverage[{index}].profileRef")
        window = item.get("window")
        status = item.get("status")
        if ref not in profile_by_ref or window != selected_window or status not in ("ok", "zero"):
            raise InputError(f"coverage[{index}] 身份、窗口或状态无效")
        key = (ref, window)
        if key in coverage:
            raise InputError("coverage 中存在重复组合")
        coverage[key] = status
    expected = {(ref, selected_window) for ref in profile_by_ref}
    if set(coverage) != expected:
        raise InputError("coverage 未覆盖本次选择的全部 Profile")

    rows_in = require_list(raw.get("rows"), "rows")
    if not rows_in:
        raise InputError("所选范围没有搜索词明细")
    row_counts = {key: 0 for key in expected}
    rows = []
    campaign_keys = {}
    portfolio_names = {}
    campaign_names = {}
    for index, value in enumerate(rows_in):
        row = require_dict(value, f"rows[{index}]")
        ref = reference(row.get("profileRef"), f"rows[{index}].profileRef")
        window = row.get("window")
        if ref not in profile_by_ref or window != selected_window:
            raise InputError(f"rows[{index}] Profile 或窗口无效")
        row_counts[(ref, window)] += 1
        query = nonempty(row.get("query"), f"rows[{index}].query")
        clicks = number(row.get("clicks"), f"rows[{index}].clicks")
        if not clicks.is_integer():
            raise InputError(f"rows[{index}].clicks 必须为整数")
        spends = optional_number(row.get("spends"), f"rows[{index}].spends")
        cvr = optional_number(row.get("cvr"), f"rows[{index}].cvr", 100)
        portfolio_status = row.get("portfolioStatus")
        if portfolio_status == "unassigned":
            if row.get("portfolioRef") is not None:
                raise InputError(f"rows[{index}] 未加入组合却包含组合 ID")
            portfolio = "未加入广告组合"
        elif portfolio_status == "assigned":
            portfolio_ref = reference(row.get("portfolioRef"), f"rows[{index}].portfolioRef")
            portfolio = nonempty(row.get("portfolio"), f"rows[{index}].portfolio")
            portfolio_identity = (ref, window, portfolio_ref)
            if portfolio_identity in portfolio_names and portfolio_names[portfolio_identity] != portfolio:
                raise InputError(f"rows[{index}] 同一广告组合 ID 的名称冲突")
            portfolio_names[portfolio_identity] = portfolio
        else:
            raise InputError(f"rows[{index}].portfolioStatus 必须明确为 assigned 或 unassigned")

        campaign_ref_value = row.get("campaignRef")
        campaign_ref = None if campaign_ref_value is None else reference(campaign_ref_value, f"rows[{index}].campaignRef")
        campaign_name = row.get("campaign")
        if not isinstance(campaign_name, str):
            campaign_name = ""
        campaign_name = campaign_name.strip()
        if campaign_ref and campaign_name:
            campaign_identity = (ref, window, campaign_ref)
            if campaign_identity in campaign_names and campaign_names[campaign_identity] != campaign_name:
                raise InputError(f"rows[{index}] 同一活动 ID 的名称冲突")
            campaign_names[campaign_identity] = campaign_name
        incomplete_identity = not campaign_ref or not campaign_name
        campaign = campaign_name or "活动信息不完整"
        identity = (ref, campaign_ref) if campaign_ref else (ref, f"missing:{index}")
        if identity not in campaign_keys:
            campaign_keys[identity] = f"c{len(campaign_keys) + 1}"
        group_name = row.get("group")
        group = group_name.strip() if isinstance(group_name, str) else ""
        p = profile_by_ref[ref]
        rows.append({
            "window": window, "query": query, "profile": p["key"],
            "site": p["site"], "country": p["country"], "currency": p["currency"],
            "shop": p["shop"], "portfolio": portfolio, "campaign": campaign,
            "campaignKey": campaign_keys[identity], "group": group, "clicks": int(clicks),
            "spends": spends, "cvr": cvr, "incompleteIdentity": incomplete_identity,
        })

    for key, status in coverage.items():
        count = row_counts[key]
        if (status == "zero") != (count == 0):
            raise InputError("coverage 状态与实际明细行数冲突")
    return {"sites": sites, "dateWindows": [w for w in windows if w["key"] == selected_window],
            "profiles": profiles, "rows": rows, "initialWindow": selected_window,
            "timezone": timezone,
            "initialSelection": {"date": selected_window, "site": scope["site"],
                                 "country": scope["country"],
                                 "store": profile_by_ref[selected_ref]["key"] if selected_ref else ""}}


def render(raw: dict) -> bytes:
    payload = normalize(raw)
    template_bytes = TEMPLATE.read_bytes()
    digest = hashlib.sha256(template_bytes).hexdigest()
    if digest != TEMPLATE_SHA256:
        raise InputError("标准模板指纹不匹配，停止生成以避免版式漂移")
    template = template_bytes.decode("utf-8")
    if template.count("__LOGO_BASE64__") != 1 or template.count("__DASHBOARD_PAYLOAD__") != 1:
        raise InputError("标准模板数据插槽不完整")
    logo = base64.b64encode(LOGO.read_bytes()).decode("ascii")
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    data = (data.replace("&", "\\u0026").replace("<", "\\u003c")
                .replace(">", "\\u003e").replace("\u2028", "\\u2028")
                .replace("\u2029", "\\u2029"))
    output = template.replace("__LOGO_BASE64__", logo).replace("__DASHBOARD_PAYLOAD__", data)
    if "__DASHBOARD_PAYLOAD__" in output or "__LOGO_BASE64__" in output:
        raise InputError("输出仍有模板占位符")
    return output.encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="经领星 MCP 验证的规范化 JSON")
    parser.add_argument("--output", required=True, type=Path, help="单文件离线 HTML，必须在 Skill 包外")
    parser.add_argument("--check", action="store_true", help="只比较既有 HTML 与标准渲染结果")
    args = parser.parse_args()
    try:
        source = args.input.resolve()
        output = args.output.resolve()
        if source == output:
            raise InputError("HTML 输出不能覆盖本次报告输入 JSON")
        if ROOT == source or ROOT in source.parents:
            raise InputError("含源身份的输入 JSON 不得写入公开 Skill 包")
        if ROOT == output or ROOT in output.parents:
            raise InputError("真实看板输出不得写入公开 Skill 包")
        raw = require_dict(json.loads(source.read_text(encoding="utf-8")), "输入 JSON")
        generated = render(raw)
        if args.check:
            if output.read_bytes() != generated:
                raise InputError("既有 HTML 与标准模板渲染结果不一致")
            print("PASS: 看板与标准模板及当前输入完全一致")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(generated)
            print(f"PASS: {output} ({len(generated)} bytes)")
        return 0
    except (InputError, OSError, json.JSONDecodeError, UnicodeError) as error:
        print(f"STOP: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
