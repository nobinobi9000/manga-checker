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

JST = ZoneInfo("Asia/Tokyo")


# ==============================
# Supabase
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
# 巻数抽出
# ==============================
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
                "image_url": book.get("largeImageUrl")
            })

    if not candidates:
        return None

    return max(candidates, key=lambda x: x["vol"])


# ==============================
# LINE通知
# ==============================
def send_line_message(user_id, message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": user_id,
        "messages": [{
            "type": "text",
            "text": message
        }]
    }
    requests.post(url, headers=headers, json=payload)


# ==============================
# メイン処理
# ==============================
def check_new_manga():
    print("🚀 マンガチェック開始:", datetime.now(JST))

    manga_list = get_supabase_data()
    today = datetime.now(JST).date()

    countdown_list = []

    for manga in manga_list:
        id = manga["id"]
        user_id = manga["user_id"]
        title = manga["title_key"]
        last_vol = manga.get("last_purchased_vol", 0)
        is_reserved = manga.get("is_reserved", False)
        sales_date_str = manga.get("sales_date")

        # ---------------------------
        # 新刊検知
        # ---------------------------
        latest = fetch_latest_info(title, last_vol)

        if latest:
            print("📘 新刊発見:", title, latest["vol"])

            update_supabase(id, {
                "isbn": latest["isbn"],
                "sales_date": latest["sales_date"],
                "image_url": latest["image_url"],
                "is_reserved": False
            })

            send_line_message(
                user_id,
                f"📢 新刊発見！\n{title} {latest['vol']}巻\n発売日: {latest['sales_date']}"
            )

        # ---------------------------
        # 発売日処理
        # ---------------------------
        if sales_date_str:
            try:
                sales_date = datetime.strptime(
                    sales_date_str.replace("年", "-").replace("月", "-").replace("日", ""),
                    "%Y-%m-%d"
                ).date()

                days_left = (sales_date - today).days

                # 発売日翌日 → 自動巻数更新
                if days_left == -1:
                    update_supabase(id, {
                        "last_purchased_vol": last_vol + 1
                    })

                # 予約済みは通知しない
                if is_reserved:
                    continue

                # カウントダウン
                if days_left in [7, 1, 0]:
                    countdown_list.append(
                        f"{title}\nあと{days_left}日"
                    )

            except:
                pass

    # まとめ通知
    if countdown_list:
        send_line_message(
            manga_list[0]["user_id"],
            "📅 発売日カウントダウン\n\n" + "\n\n".join(countdown_list)
        )

    print("✨ マンガチェック完了:", datetime.now(JST))


if __name__ == "__main__":
    check_new_manga()
