#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
매일 평일 오전 8:30 입고 예정 품목 Slack 알림 (Block Kit 버전)
"""
import streamlit as st
import pandas as pd
import requests
import datetime
import pytz
from utils.db_functions import get_source_data


# --- 데이터 조회 ---
def fetch_incoming_items():
    """ERP에서 7일 이내 입고 예정 품목 조회"""
    df = get_source_data()
    if df.empty:
        return None

    today = pd.Timestamp.now().normalize()
    df = df[df["입고예정일"] >= today]
    return df.sort_values(["입고예정일", "브랜드", "품명"])


# --- Slack Block Kit 메시지 구성 ---
def build_slack_blocks(df: pd.DataFrame):
    grouped = df.groupby("입고예정일")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📦 오늘의 입고 예정 품목 안내", "emoji": True},
        },
        {"type": "divider"},
    ]

    for date, sub in grouped:
        date_str = date.strftime("%Y-%m-%d")
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"🗓️ *{date_str}*"},
            }
        )

        # 브랜드별 정리
        brand_groups = sub.groupby("브랜드")
        for brand, items in brand_groups:
            table_lines = []
            for _, r in items.iterrows():
                po = r.get("발주번호", "-")
                line = (
                    f"• *{r['품명']}* ({r.get('버전','')})  "
                    f"→ {r['예정수량']:,}개  |  `PO:{po}`"
                )
                table_lines.append(line)

            brand_text = f"*{brand}*\n" + "\n".join(table_lines)
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": brand_text},
                }
            )

        blocks.append({"type": "divider"})

    return {"blocks": blocks}


# --- Slack 전송 함수 ---
def send_to_slack(blocks_payload):
    url = st.secrets["slack_webhook_url"]
    try:
        res = requests.post(url, json=blocks_payload)
        if res.status_code != 200:
            st.error(f"Slack 전송 실패: {res.status_code}, {res.text}")
        else:
            st.success("✅ Slack 알림 전송 완료")
    except Exception as e:
        st.error(f"Slack 전송 오류: {e}")


# --- 실행 메인 ---
def main():
    tz = pytz.timezone("Asia/Seoul")
    now = datetime.datetime.now(tz)
    weekday = now.weekday()  # 0=월, 6=일

    if weekday >= 5:
        st.info("주말에는 Slack 알림을 전송하지 않습니다.")
        return

    df = fetch_incoming_items()
    if df is None or df.empty:
        msg = {"text": "📭 오늘은 입고 예정 품목이 없습니다."}
        send_to_slack(msg)
        return

    payload = build_slack_blocks(df)
    send_to_slack(payload)


if __name__ == "__main__":
    main()
