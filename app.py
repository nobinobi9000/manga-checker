import os
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# =============================
# 環境変数
# =============================
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
LINE_ACCESS_TOKEN = os.environ["LINE_ACCESS_TOKEN"]
ADMIN_LINE_USER_ID = os.environ["ADMIN_LINE_USER_ID"]
RAKUTEN_APP_ID = os.environ["RAKUTEN_APP_ID"]
RAKUTEN_AFFILIATE_ID = os.environ["RAKUTEN_AFFILIATE_ID"]

JST = ZoneInfo("Asia/Tokyo")

# =============================
# Supabase 共通
# =============================

def supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

def get_manga_list():
    url = f"{SUPABASE_URL}/rest/v1/manga_list?select=*"
    res = requests.get(url, headers=supabase_headers())
    return res.json()

def update_manga(id, data):
    url = f"{SUPABASE_URL}/rest/v1/manga_list?id=eq.{id}"
    requests.patch(url, headers=supabase_headers(), json=data)

# =============================
# 楽天API検索
# =============================

def rakuten_search(title):
    url = "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "title": title,
        "format": "json"
    }
    res = requests.get(url, params=params)
    data = res.json()
    if data["count"] > 0:
        return data["Items"][0]["Item"]
    return None

# =============================
# アフィリエイトURL生成
# =============================

def build_amazon_url(isbn):
    return f"https://www.amazon.co.jp/dp/{isbn}/?tag=nobinobi9000-22"

def build_rakuten_url(item_url):
    return f"https://hb.afl.rakuten.co.jp/hgc/{RAKUTEN_AFFILIATE_ID}/?pc={item_url}"

# =============================
# LINE通知
# =============================

def push_line(messages):
    headers = {
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "to": ADMIN_LINE_USER_ID,
        "messages": messages
    }
    requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers=headers,
        json=data
    )

def build_single_notification(item):
    amazon_url = build_amazon_url(item["isbn"])
    rakuten_url = build_rakuten_url(item["itemUrl"])

    return {
        "type": "flex",
        "altText": f"{item['title']} 新刊発見！",
        "contents": {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": item["largeImageUrl"],
                "size": "full",
                "aspectRatio": "1:1",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": item["title"], "weight": "bold", "wrap": True},
                    {"type": "text", "text": f"発売日: {item['salesDate']}", "color": "#FF5551"}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#FF9900",
                        "action": {
                            "type": "uri",
                            "label": "Amazonで予約",
                            "uri": amazon_url
                        }
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "action": {
                            "type": "uri",
                            "label": "楽天で予約",
                            "uri": rakuten_url
                        }
                    }
                ]
            }
        }
    }

# =============================
# メイン処理
# =============================

def check_manga():
    print("🚀 マンガチェック開始:", datetime.now(JST))

    manga_list = get_manga_list()
    today = datetime.now(JST).date()

    new_release_notifications = []
    countdown_notifications = []

    for manga in manga_list:
        if manga["is_reserved"]:
            continue

        rakuten = rakuten_search(manga["title_key"])
        if not rakuten:
            continue

        new_isbn = rakuten["isbn"]
        new_date_str = rakuten["salesDate"]
        new_date = datetime.strptime(new_date_str, "%Y年%m月%d日").date()

        # 発売日過去はスキップ
        if new_date < today:
            continue

        # 新刊検知
        if new_isbn != manga["isbn"]:
            update_manga(manga["id"], {
                "isbn": new_isbn,
                "sales_date": new_date_str,
                "image_url": rakuten["largeImageUrl"],
                "is_reserved": False
            })

            new_release_notifications.append(
                build_single_notification(rakuten)
            )
            continue

        # カウントダウン
        days_left = (new_date - today).days
        if days_left in [30, 14, 7, 0]:
            countdown_notifications.append(
                build_single_notification(rakuten)
            )

    # 新刊通知（単独）
    for msg in new_release_notifications:
        push_line([msg])

    # カウントダウン（まとめてカルーセル）
    if countdown_notifications:
        push_line([
            {
                "type": "flex",
                "altText": "発売日が近づいています！",
                "contents": {
                    "type": "carousel",
                    "contents": [msg["contents"] for msg in countdown_notifications]
                }
            }
        ])

    print("✨ 完了:", datetime.now(JST))


if __name__ == "__main__":
    check_manga()
