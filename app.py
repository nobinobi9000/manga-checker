import os
import json
import requests
import urllib.parse
import re
from datetime import datetime

# --- 設定 ---
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
LINE_NOTIFY_TOKEN = os.environ.get('LINE_NOTIFY_TOKEN')
AMAZON_TRACKING_ID = "nobinobi9000-22"

def clean_title(title):
    """タイトルから出版社などのノイズを消す"""
    # 「ブルーロック 講談社」のような入力から出版社名を削除
    keywords = ["講談社", "集英社", "小学館", "KADOKAWA", "白泉社", "秋田書店"]
    for k in keywords:
        title = title.replace(k, "")
    return title.strip()

def check_new_manga():
    if not os.path.exists('history.json'):
        print("history.jsonが見つかりません。")
        return

    with open('history.json', 'r', encoding='utf-8') as f:
        history = json.load(f)

    updated = False
    today = datetime.now().strftime('%Y%m%d')

    for title, info in history.items():
        # --- 検索ワードの組み立て（作品名 ＋ 作者名） ---
        pure_title = clean_title(title)
        author = info.get('author', '')
        search_query = f"{pure_title} {author}".strip()
        
        encoded_query = urllib.parse.quote(search_query)
        # 漫画（001001）ジャンルに限定して検索精度を最大化
        url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?format=json&title={encoded_query}&applicationId={RAKUTEN_APP_ID}&booksGenreId=001001"
        
        try:
            res = requests.get(url)
            if res.status_code == 200:
                data = res.json()
                if data.get('items'):
                    item = data['items'][0]['Item']
                    new_isbn = item.get('isbn', '0')
                    sales_date = item.get('salesDate', '')
                    last_notified = info.get('last_notified', '')
                    
                    # ISBNが0、または新しい発売日がある場合に更新
                    if str(info.get('isbn')) == "0" or (sales_date and sales_date > last_notified):
                        history[title]['isbn'] = new_isbn
                        history[title]['salesDate'] = sales_date
                        history[title]['last_notified'] = today
                        updated = True
                        
                        amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                        message = (
                            f"\n【新刊・登録情報】\n"
                            f"『{item['title']}』\n"
                            f"著：{item['author']}\n"
                            f"発売日：{sales_date}\n\n"
                            f"▼Amazonで購入\n{amazon_url}"
                        )
                        send_line(message)
                        print(f"✅ 取得成功: {search_query}")
                else:
                    print(f"⚠️ 検索ヒットなし: {search_query}")
            else:
                print(f"❌ APIエラー({res.status_code}): {title}")
                if not RAKUTEN_APP_ID:
                    print("警告: RAKUTEN_APP_ID が空です。")
        except Exception as e:
            print(f"‼️ 例外: {e}")

    if updated:
        with open('history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
        print("💾 history.jsonを更新保存しました。")

def send_line(message):
    if not LINE_NOTIFY_TOKEN: return
    requests.post("https://notify-bot.line.me/api/notify", 
                  headers={"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}, 
                  data={"message": message})

if __name__ == "__main__":
    check_new_manga()
