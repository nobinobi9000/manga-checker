import os
import requests
from datetime import datetime, timedelta, timezone

# ========= 環境変数 =========
RAKUTEN_APP_ID = os.getenv("RAKUTEN_APP_ID")
RAKUTEN_AFFILIATE_ID = os.getenv("RAKUTEN_AFFILIATE_ID")
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

JST = timezone(timedelta(hours=9))


# ========= Supabase取得 =========
def get_supabase_data():
    url = f"{SUPABASE_URL}/rest/v1/manga_list?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()


# ========= Supabase更新 =========
def update_last_notified(record_id):
    url = f"{SUPABASE_URL}/rest/v1/manga_list?id=eq.{record_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    today = datetime.now(JST).date().isoformat()
    data = {"last_notified": today}
    requests.patch(url, headers=headers, json=data)


# ========= LINE通知 =========
def send_line_message(user_id, message, image_url=None):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    messages = [{"type": "text", "text": message}]

    if image_url:
        messages.append({
            "type": "image",
            "originalContentUrl": image_url,
            "previewImageUrl": image_url
        })

    body = {
        "to": user_id,
        "messages": messages
    }

    res = requests.post(url, headers=headers, json=body)
    res.raise_for_status()


# ========= 日付パース（日本語対応） =========
def parse_sales_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y年%m月%d日").date()
    except Exception:
        print(f"⚠️ 日付パース失敗: {date_str}")
        return None


# ========= 楽天API検索 =========
def fetch_latest_info(title):
    url = "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "affiliateId": RAKUTEN_AFFILIATE_ID,
        "title": title,
        "hits": 1
    }

    res = requests.get(url, params=params)
    res.raise_for_status()
    data = res.json()

    if data["Items"]:
        item = data["Items"][0]["Item"]
        return {
            "isbn": item.get("isbn"),
            "sales_date": item.get("salesDate"),
            "image_url": item.get("largeImageUrl") or item.get("mediumImageUrl")
        }

    return None


# ========= メイン処理 =========
def check_new_manga():
    now = datetime.now(JST)
    today = now.date()

    print(f"🚀 マンガチェック開始: {now}")
    print("📚 Supabaseデータ取得中...")

    manga_list = get_supabase_data()
    notify_count = 0

    for item in manga_list:
        record_id = item["id"]
        user_id = item["user_id"]
        title = item["title_key"]
        sales_date_str = item["sales_date"]
        last_notified = item["last_notified"]

        release_date = parse_sales_date(sales_date_str)
        if not release_date:
            continue

        diff = (release_date - today).days

        # 通知対象日
        notify_days = [30, 14, 7, 0]

        if diff in notify_days:
            # 既に今日通知済みならスキップ
            if last_notified == today.isoformat():
                continue

            print(f"📢 通知対象: {title} (diff={diff})")

            latest = fetch_latest_info(title)
            image_url = item.get("image_url")

            message = f"📚 {title}\n"
            if diff == 0:
                message += "🎉 本日発売！"
            else:
                message += f"⏳ 発売まであと {diff} 日"

            send_line_message(user_id, message, image_url)
            update_last_notified(record_id)

            notify_count += 1

    print(f"📊 通知件数: {notify_count}")
    print(f"✨ マンガチェック完了: {datetime.now(JST)}")


# ========= 実行 =========
if __name__ == "__main__":
    check_new_manga()
