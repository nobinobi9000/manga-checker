import os
import requests
from datetime import datetime
import time

# --- 設定（GitHub Secretsに登録するもの） ---
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID', '').strip()
LINE_ACCESS_TOKEN = os.environ.get('LINE_ACCESS_TOKEN', '').strip() # Messaging API用
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').strip()
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '').strip()
AMAZON_TRACKING_ID = "nobinobi9000-22"

def get_supabase_data():
    """Supabaseから全ユーザーのマンガリストを取得"""
    url = f"{SUPABASE_URL}/rest/v1/manga_list?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    response = requests.get(url, headers=headers)
    return response.json()

def update_supabase_data(row_id, update_data):
    """通知日やISBNを更新"""
    url = f"{SUPABASE_URL}/rest/v1/manga_list?id=eq.{row_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    requests.patch(url, headers=headers, json=update_data)

def check_new_manga():
    manga_list = get_supabase_data()
    today = datetime.now()
    today_num = today.strftime('%Y%m%d')

    for item in manga_list:
        # 予約済み(is_reserved=True)ならスキップ
        if item.get('is_reserved'):
            continue

        user_id = item['user_id']
        row_id = item['id']
        pure_title = item['title_key']
        author_name = item.get('author', '')
        stored_isbn = item.get('isbn', '')
        last_notified = item.get('last_notified', '')

        # 楽天APIで検索
        url = "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
        params = {
            "applicationId": RAKUTEN_APP_ID,
            "format": "json",
            "title": pure_title,
            "author": author_name,
            "sort": "-releaseDate",
            "booksGenreId": "001001"
        }

        try:
            res = requests.get(url, params=params)
            data = res.json()
            if "Items" in data and len(data["Items"]) > 0:
                found = data["Items"][0]["Item"]
                new_isbn = found['isbn']
                raw_date = found['salesDate']
                
                # 日付変換
                try:
                    sales_date_dt = datetime.strptime(raw_date, '%Y年%m月%d日')
                    sales_date_num = sales_date_dt.strftime('%Y%m%d')
                    days_left = (sales_date_dt - today).days
                except:
                    sales_date_num = ""
                    days_left = 999

                # 通知判定（ルール維持）
                notify_type = None
                if new_isbn != stored_isbn:
                    notify_type = "🌟【新刊情報】"
                elif days_left == 30: notify_type = "📅【30日前】"
                elif days_left == 14: notify_type = "📅【14日前】"
                elif days_left == 7:  notify_type = "📅【7日前】"
                elif days_left == 0:  notify_type = "🔥【本日発売】"

                # 重複通知防止チェック
                if notify_type and last_notified != today_num:
                    affiliate_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                    message = f"{notify_type}\n{found['title']}\n発売日: {raw_date}\n\nAmazonで予約・購入👇\n{affiliate_url}"
                    
                    if send_line_push(user_id, message):
                        # データベース更新
                        update_supabase_data(row_id, {
                            "isbn": new_isbn,
                            "sales_date": raw_date,
                            "last_notified": today_num
                        })
            
            time.sleep(1) # API負荷軽減
        except Exception as e:
            print(f"Error checking {pure_title}: {e}")

def send_line_push(user_id, message):
    """特定のユーザーにのみメッセージを送る"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": message}]
    }
    res = requests.post(url, headers=headers, json=payload)
    return res.status_code == 200

if __name__ == "__main__":
    check_new_manga()
