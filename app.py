import os
import requests
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ==============================
# 環境変数
# ==============================
RAKUTEN_APP_ID = os.getenv("RAKUTEN_APP_ID")
RAKUTEN_AFFILIATE_ID = os.getenv("RAKUTEN_AFFILIATE_ID")
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_LINE_USER_ID = os.getenv("ADMIN_LINE_USER_ID")

JST = ZoneInfo("Asia/Tokyo")


# ==============================
# Supabase操作
# ==============================
def get_supabase_data():
    url = f"{SUPABASE_URL}/rest/v1/manga_list?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()


def update_supabase(id, payload):
    url = f"{SUPABASE_URL}/rest/v1/manga_list?id=eq.{id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    requests.patch(url, headers=headers, json=payload)


# ==============================
# ユーティリティ
# ==============================
def normalize_image_url(url):
    if not url or "noimage" in url:
        return None
    return url.replace("_ex=200x200", "_ex=600x600")


def extract_vol_from_title(title):
    if not title:
        return None

    z2h = str.maketrans("０１２３４５６７８９", "0123456789")
    title = title.translate(z2h)

    patterns = [
        r'\((\d+)\)',
        r'第\s*(\d+)\s*巻',
        r'(\d+)\s*巻',
        r'\s(\d+)\b',
        r'(\d+)$'
    ]

    for pattern in patterns:
        m = re.search(pattern, title)
        if m:
            return int(m.group(1))

    return None


def is_special_edition(title):
    keywords = ["特装", "限定", "豪華", "小冊子", "同梱", "DVD", "Blu-ray"]
    return any(k in title for k in keywords)


# ==============================
# 楽天API
# ==============================
def fetch_latest_info(title, last_vol):
    url = "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "affiliateId": RAKUTEN_AFFILIATE_ID,
        "title": title,
        "format": "json"
    }

    res = requests.get(url, params=params)
    data = res.json()

    if not data.get("Items"):
        return None

    candidates = []

    for item in data["Items"]:
        book = item["Item"]
        book_title = book.get("title", "")

        if is_special_edition(book_title):
            continue

        vol = extract_vol_from_title(book_title)
        if not vol:
            continue

        if vol > last_vol:
            candidates.append({
                "vol": vol,
                "isbn": book.get("isbn"),
                "sales_date": book.get("salesDate"),
                "image_url": book.get("largeImageUrl"),
                "item_url": book.get("itemUrl")
            })

    if not candidates:
        return None

    return max(candidates, key=lambda x: x["vol"])


# ==============================
# LINE通知
# ==============================
def push_line(payload):
    requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        },
        json=payload
    )


def send_error(message):
    if not ADMIN_LINE_USER_ID:
        return
    push_line({
        "to": ADMIN_LINE_USER_ID,
        "messages": [{
            "type": "text",
            "text": f"🚨 エラー発生\n{message}"
        }]
    })


def send_new_release(user_id, title, vol, sales_date, image_url, item_url):
    image_url = normalize_image_url(image_url)

    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": title, "weight": "bold", "wrap": True},
                {"type": "text", "text": f"{vol}巻"},
                {"type": "text", "text": f"発売日: {sales_date}"}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "action": {
                        "type": "uri",
                        "label": "楽天で見る",
                        "uri": item_url
                    }
                }
            ]
        }
    }

    if image_url:
        bubble["hero"] = {
            "type": "image",
            "url": image_url,
            "size": "full",
            "aspectRatio": "1:1",
            "aspectMode": "cover"
        }

    push_line({
        "to": user_id,
        "messages": [{
            "type": "flex",
            "altText": "新刊発見",
            "contents": bubble
        }]
    })


def send_countdown_carousel(user_id, items):
    bubbles = []

    for item in items:
        image_url = normalize_image_url(item["image_url"])

        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {"type": "text", "text": item["title"], "weight": "bold", "wrap": True},
                    {"type": "text", "text": f"あと{item['days']}日", "color": "#FF5555"},
                    {"type": "text", "text": f"発売日: {item['sales_date']}"}
                ]
            }
        }

        if image_url:
            bubble["hero"] = {
                "type": "image",
                "url": image_url,
                "size": "full",
                "aspectRatio": "1:1",
                "aspectMode": "cover"
            }

        bubbles.append(bubble)

    push_line({
        "to": user_id,
        "messages": [{
            "type": "flex",
            "altText": "発売日カウントダウン",
            "contents": {
                "type": "carousel",
                "contents": bubbles
            }
        }]
    })


# ==============================
# メイン処理
# ==============================
def check_new_manga():
    print("🚀 マンガチェック開始:", datetime.now(JST))

    manga_list = get_supabase_data()
    today = datetime.now(JST).date()

    for manga in manga_list:
        id = manga["id"]
        user_id = manga["user_id"]
        title = manga["title_key"]
        last_vol = manga.get("last_purchased_vol", 0)
        is_reserved = manga.get("is_reserved", False)

        latest = fetch_latest_info(title, last_vol)

        if latest:
            update_supabase(id, {
                "isbn": latest["isbn"],
                "sales_date": latest["sales_date"],
                "image_url": latest["image_url"],
                "is_reserved": False
            })

            send_new_release(
                user_id,
                title,
                latest["vol"],
                latest["sales_date"],
                latest["image_url"],
                latest["item_url"]
            )

    print("✨ マンガチェック完了:", datetime.now(JST))


if __name__ == "__main__":
    try:
        check_new_manga()
    except Exception as e:
        send_error(str(e))
        raise
