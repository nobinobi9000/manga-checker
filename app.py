import os
import requests
from datetime import datetime, timedelta, timezone

# =========================
# 環境変数
# =========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
RAKUTEN_APP_ID = os.getenv("RAKUTEN_APP_ID")
RAKUTEN_AFFILIATE_ID = os.getenv("RAKUTEN_AFFILIATE_ID")
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")

JST = timezone(timedelta(hours=9))

# =========================
# 共通
# =========================
def parse_sales_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y年%m月%d日").date()
    except:
        return None

def get_supabase_data():
    url = f"{SUPABASE_URL}/rest/v1/manga_list?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    res = requests.get(url, headers=headers)
    return res.json()

def patch_supabase(record_id, data):
    url = f"{SUPABASE_URL}/rest/v1/manga_list?id=eq.{record_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    requests.patch(url, headers=headers, json=data)

# =========================
# 楽天API
# =========================
def fetch_latest_info(title):
    url = "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "affiliateId": RAKUTEN_AFFILIATE_ID,
        "title": title,
        "format": "json",
        "sort": "-releaseDate"
    }

    res = requests.get(url, params=params)
    data = res.json()

    if not data.get("Items"):
        return None

    # 発売日が一番新しいものを取得
    latest_item = max(
        data["Items"],
        key=lambda x: parse_sales_date(x["Item"].get("salesDate", "")) or datetime.min.date()
    )["Item"]

    return {
        "isbn": latest_item.get("isbn"),
        "sales_date": latest_item.get("salesDate"),
        "image_url": latest_item.get("largeImageUrl"),
    }

# =========================
# LINE送信
# =========================
def send_text(user_id, message):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }

    payload = {
        "to": user_id,
        "messages": [{
            "type": "text",
            "text": message
        }]
    }

    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=payload)

def send_carousel(user_id, items):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }

    columns = []
    for item in items[:10]:  # 最大10件
        columns.append({
            "thumbnailImageUrl": item["image_url"],
            "title": item["title"][:40],
            "text": f"発売日: {item['sales_date']}"[:60],
            "actions": [{
                "type": "message",
                "label": "予約した",
                "text": f"予約済み:{item['title']}"
            }]
        })

    payload = {
        "to": user_id,
        "messages": [{
            "type": "template",
            "altText": "発売日が近い作品があります",
            "template": {
                "type": "carousel",
                "columns": columns
            }
        }]
    }

    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=payload)

# =========================
# メイン処理
# =========================
def check_new_manga():
    now = datetime.now(JST)
    today = now.date()

    print(f"🚀 チェック開始: {now}")

    manga_list = get_supabase_data()

    new_release_notifications = []
    countdown_notifications = []

    for item in manga_list:
        record_id = item["id"]
        user_id = item["user_id"]
        title = item["title_key"]
        current_isbn = item.get("isbn")
        is_reserved = item.get("is_reserved", False)

        # =========================
        # 最新情報取得
        # =========================
        latest = fetch_latest_info(title)
        if not latest:
            continue

        latest_isbn = latest["isbn"]

        # =========================
        # 🆕 新刊検知
        # =========================
        if latest_isbn and latest_isbn != current_isbn:
            print(f"🆕 新刊検知: {title}")

            patch_supabase(record_id, {
                "isbn": latest["isbn"],
                "sales_date": latest["sales_date"],
                "image_url": latest["image_url"],
                "is_reserved": False,
                "last_notified": None
            })

            new_release_notifications.append({
                "user_id": user_id,
                "title": title,
                "sales_date": latest["sales_date"],
                "image_url": latest["image_url"]
            })

            continue

        # =========================
        # 発売日取得
        # =========================
        release_date = parse_sales_date(item.get("sales_date", ""))
        if not release_date:
            continue

        diff = (release_date - today).days

        # =========================
        # 発売日翌日に予約フラグリセット
        # =========================
        if today > release_date and is_reserved:
            patch_supabase(record_id, {"is_reserved": False})
            continue

        # =========================
        # ⏳ カウントダウン通知
        # =========================
        if diff in [30, 14, 7, 0] and not is_reserved:
            countdown_notifications.append({
                "user_id": user_id,
                "title": title,
                "sales_date": item["sales_date"],
                "image_url": item.get("image_url")
            })

    # =========================
    # 🆕 新刊通知（単独）
    # =========================
    for notice in new_release_notifications:
        message = f"""🆕 新刊発売決定！

{notice['title']}
発売日: {notice['sales_date']}

予約を忘れていませんか？📚
"""
        send_text(notice["user_id"], message)

    # =========================
    # ⏳ カウントダウン（ユーザーごとにまとめる）
    # =========================
    grouped = {}
    for item in countdown_notifications:
        grouped.setdefault(item["user_id"], []).append(item)

    for user_id, items in grouped.items():
        send_carousel(user_id, items)

    print(f"✨ チェック完了: {datetime.now(JST)}")


if __name__ == "__main__":
    check_new_manga()
