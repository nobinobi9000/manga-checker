import os
import requests
from datetime import datetime
import time

# --- 設定（GitHub Secretsに登録するもの） ---
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID', '').strip()
LINE_ACCESS_TOKEN = os.environ.get('LINE_ACCESS_TOKEN', '').strip()
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').strip()
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '').strip()
AMAZON_TRACKING_ID = "nobinobi9000-22"
RAKUTEN_AFFILIATE_ID = os.environ.get('RAKUTEN_AFFILIATE_ID', '').strip()  # 楽天アフィリエイトID

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
    """通知日、ISBN、発売日を更新"""
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
        stored_sales_date = item.get('sales_date', '')
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
                image_url = found.get('largeImageUrl', found.get('mediumImageUrl', ''))
                
                # 日付変換
                try:
                    sales_date_dt = datetime.strptime(raw_date, '%Y年%m月%d日')
                    sales_date_num = sales_date_dt.strftime('%Y%m%d')
                    days_left = (sales_date_dt - today).days
                except:
                    sales_date_num = ""
                    days_left = 999

                # 通知判定ルール
                notify_type = None
                is_data_updated = False
                
                # 🌟 新刊情報（ISBNまたは発売日が変更された場合）
                if new_isbn != stored_isbn or raw_date != stored_sales_date:
                    notify_type = "🌟【新刊情報更新】" if stored_isbn else "🌟【新刊情報】"
                    is_data_updated = True
                # 📅 リマインダー
                elif days_left == 30: notify_type = "📅【30日前】"
                elif days_left == 14: notify_type = "📅【14日前】"
                elif days_left == 7:  notify_type = "📅【7日前】"
                elif days_left == 0:  notify_type = "🔥【本日発売】"

                # 重複通知防止チェック（データ更新時は再通知OK）
                should_notify = notify_type and (is_data_updated or last_notified != today_num)
                
                if should_notify:
                    # Amazonアフィリエイトリンク
                    amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                    
                    # 楽天アフィリエイトリンク
                    rakuten_url = f"https://hb.afl.rakuten.co.jp/hgc/{RAKUTEN_AFFILIATE_ID}/?pc=https%3A%2F%2Fbooks.rakuten.co.jp%2Frb%2F{new_isbn}%2F" if RAKUTEN_AFFILIATE_ID else f"https://books.rakuten.co.jp/rb/{new_isbn}/"
                    
                    # 変更内容を表示（更新時のみ）
                    update_info = ""
                    if is_data_updated and stored_isbn:
                        changes = []
                        if new_isbn != stored_isbn:
                            changes.append(f"ISBN: {stored_isbn} → {new_isbn}")
                        if raw_date != stored_sales_date:
                            changes.append(f"発売日: {stored_sales_date} → {raw_date}")
                        if changes:
                            update_info = "\n\n📝 変更内容:\n" + "\n".join(changes)
                    
                    message_text = f"{notify_type}\n{found['title']}\n発売日: {raw_date}{update_info}\n\n📚 予約・購入はこちら👇\n楽天: {rakuten_url}\nAmazon: {amazon_url}"
                    
                    # 画像付きメッセージで送信（サムネイルサイズに調整）
                    if send_line_push_with_image(user_id, message_text, image_url):
                        # データベース更新
                        update_supabase_data(row_id, {
                            "isbn": new_isbn,
                            "sales_date": raw_date,
                            "last_notified": today_num
                        })
                        print(f"✅ 通知送信: {pure_title} ({notify_type})")
            
            time.sleep(1)  # API負荷軽減
        except Exception as e:
            print(f"❌ Error checking {pure_title}: {e}")

def send_line_push_with_image(user_id, message_text, image_url):
    """画像付きメッセージを送信（サムネイルサイズで表示）"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    messages = []
    
    # 画像がある場合は小さいプレビューで送信
    if image_url:
        messages.append({
            "type": "image",
            "originalContentUrl": image_url,
            "previewImageUrl": image_url
        })
    
    # テキストメッセージを追加
    messages.append({
        "type": "text",
        "text": message_text
    })
    
    payload = {
        "to": user_id,
        "messages": messages
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload)
        return res.status_code == 200
    except Exception as e:
        print(f"LINE送信エラー: {e}")
        return False

if __name__ == "__main__":
    print(f"🚀 マンガチェック開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    check_new_manga()
    print(f"✨ マンガチェック完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
