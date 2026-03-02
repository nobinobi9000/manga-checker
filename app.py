import os
import requests
from datetime import datetime, timedelta, timezone
import time

# ===== 設定（GitHub Secrets） =====
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID', '').strip()
LINE_ACCESS_TOKEN = os.environ.get('LINE_ACCESS_TOKEN', '').strip()
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').strip()
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '').strip()
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID', '').strip()
AMAZON_TRACKING_ID = "nobinobi9000-22"

JST = timezone(timedelta(hours=9))


# ===== Supabase操作 =====
def get_supabase_data():
    url = f"{SUPABASE_URL}/rest/v1/manga_list?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()


def update_supabase_data(row_id, update_data):
    url = f"{SUPABASE_URL}/rest/v1/manga_list?id=eq.{row_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    res = requests.patch(url, headers=headers, json=update_data)
    res.raise_for_status()


# ===== LINE送信 =====
def send_line_carousel(user_id, items):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }

    bubbles = []

    for item in items[:10]:
        bubble = {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": item['image_url'] if item['image_url']
                else "https://via.placeholder.com/1040x1040/CCCCCC/FFFFFF?text=No+Image",
                "size": "full",
                "aspectRatio": "1:1",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": item['type'],
                        "weight": "bold",
                        "size": "sm",
                        "color": "#FF6B6B"
                    },
                    {
                        "type": "text",
                        "text": item['title'],
                        "weight": "bold",
                        "size": "md",
                        "wrap": True,
                        "margin": "md"
                    },
                    {
                        "type": "text",
                        "text": f"発売日: {item['sales_date']}",
                        "size": "sm",
                        "color": "#999999",
                        "margin": "sm"
                    }
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
                        "color": "#C8102E",
                        "action": {
                            "type": "uri",
                            "label": "楽天で見る",
                            "uri": item['rakuten_url']
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#FF9900",
                        "action": {
                            "type": "uri",
                            "label": "Amazonで見る",
                            "uri": item['amazon_url']
                        }
                    }
                ]
            }
        }
        bubbles.append(bubble)

    payload = {
        "to": user_id,
        "messages": [{
            "type": "flex",
            "altText": f"マンガ新刊通知 {len(items)}件",
            "contents": {
                "type": "carousel",
                "contents": bubbles
            }
        }]
    }

    res = requests.post(url, headers=headers, json=payload)
    return res.status_code == 200


# ===== メイン処理 =====
def check_new_manga():
    print("📚 Supabaseデータ取得中...")
    manga_list = get_supabase_data()

    now_jst = datetime.now(JST)
    today_date = now_jst.date()
    today_num = now_jst.strftime('%Y%m%d')

    notifications = {}

    for item in manga_list:

        if item.get('is_reserved'):
            continue

        user_id = item['user_id']
        row_id = item['id']
        pure_title = item['title_key']
        author_name = item.get('author', '')
        stored_isbn = item.get('isbn', '')
        stored_sales_date = item.get('sales_date', '')
        last_notified = item.get('last_notified', '')

        try:
            rakuten_url = "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"

            params = {
                "applicationId": RAKUTEN_APP_ID,
                "format": "json",
                "title": pure_title,
                "author": author_name,
                "sort": "-releaseDate",
                "booksGenreId": "001001"
            }

            res = requests.get(rakuten_url, params=params)
            data = res.json()

            if "Items" not in data or not data["Items"]:
                continue

            found = data["Items"][0]["Item"]
            new_isbn = found['isbn']
            raw_date = found['salesDate']
            image_url = found.get('largeImageUrl') or found.get('mediumImageUrl')

            try:
                sales_date_dt = datetime.strptime(raw_date, '%Y年%m月%d日')
                days_left = (sales_date_dt.date() - today_date).days
            except:
                continue

            is_data_updated = (new_isbn != stored_isbn or raw_date != stored_sales_date)

            notify_type = None
            if days_left == 30:
                notify_type = "📅【30日前】"
            elif days_left == 14:
                notify_type = "📅【14日前】"
            elif days_left == 7:
                notify_type = "📅【7日前】"
            elif days_left == 0:
                notify_type = "🔥【本日発売】"

            if notify_type and last_notified != today_num:

                if user_id not in notifications:
                    notifications[user_id] = []

                notifications[user_id].append({
                    "row_id": row_id,
                    "type": notify_type,
                    "title": found['title'],
                    "sales_date": raw_date,
                    "image_url": image_url,
                    "isbn": new_isbn,
                    "rakuten_url":
                        f"https://hb.afl.rakuten.co.jp/hgc/{RAKUTEN_AFFILIATE_ID}/?pc=https%3A%2F%2Fbooks.rakuten.co.jp%2Frb%2F{new_isbn}%2F"
                        if RAKUTEN_AFFILIATE_ID else
                        f"https://books.rakuten.co.jp/rb/{new_isbn}/",
                    "amazon_url":
                        f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                })

            elif is_data_updated:
                update_supabase_data(row_id, {
                    "isbn": new_isbn,
                    "sales_date": raw_date
                })

            time.sleep(1)

        except Exception as e:
            print(f"❌ Error checking {pure_title}: {e}")

    # ===== 通知送信 =====
    for user_id, items in notifications.items():
        if send_line_carousel(user_id, items):
            print(f"✅ 通知成功: {user_id}")

            for item in items:
                update_supabase_data(item['row_id'], {
                    "isbn": item['isbn'],
                    "sales_date": item['sales_date'],
                    "last_notified": today_num
                })
        else:
            print(f"❌ LINE送信失敗: {user_id}")


if __name__ == "__main__":
    print(f"🚀 マンガチェック開始: {datetime.now(JST)}")
    check_new_manga()
    print(f"✨ マンガチェック完了: {datetime.now(JST)}")
