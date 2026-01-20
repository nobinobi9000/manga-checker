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

def clean_text(text):
    if not text: return ""
    # 記号や出版社名を消すが、検索語としての純度を上げるため最小限にする
    text = re.sub(r'（.*?）|\(.*?\)|［.*?］|\[.*?\]', '', text)
    keywords = ["講談社", "集英社", "小学館", "KADOKAWA", "白泉社", "秋田書店", "新潮社", "スクウェア・エニックス"]
    for k in keywords:
        text = text.replace(k, "")
    return text.strip()

def get_rakuten_item(query, author_filter=""):
    """楽天APIを叩いて最適な1件を返す"""
    encoded_query = urllib.parse.quote(query)
    url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?format=json&keyword={encoded_query}&applicationId={RAKUTEN_APP_ID}&booksGenreId=001001&sort=sales"
    
    try:
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            if data.get('items'):
                # 著者名フィルターがある場合、ヒットした上位数件からチェック
                for i in range(min(3, len(data['items']))):
                    item = data['items'][i]['Item']
                    # 著者名が1文字でも含まれていれば採用
                    if not author_filter or author_filter in item.get('author', ''):
                        return item
                # フィルターで見つからなければ1番目を返す
                return data['items'][0]['Item']
        return None
    except:
        return None

def check_new_manga():
    if not os.path.exists('history.json'): return
    with open('history.json', 'r', encoding='utf-8') as f:
        history = json.load(f)

    updated = False
    today = datetime.now().strftime('%Y%m%d')

    for title, info in history.items():
        pure_title = clean_text(title)
        pure_author = clean_text(info.get('author', ''))
        
        # 1. まず「作品名 著者名」で検索
        item = get_rakuten_item(f"{pure_title} {pure_author}", pure_author)
        
        # 2. 失敗したら「作品名」だけで再検索
        if not item:
            print(f"🔄 再検索中: {pure_title}")
            item = get_rakuten_item(pure_title, pure_author)

        if item:
            new_isbn = item.get('isbn', '0')
            sales_date = item.get('salesDate', '')
            
            if str(info.get('isbn')) == "0" or (sales_date and sales_date > info.get('last_notified', '')):
                history[title]['isbn'] = new_isbn
                history[title]['salesDate'] = sales_date
                history[title]['last_notified'] = today
                updated = True
                
                amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                message = f"\n【新刊情報】\n『{item['title']}』\n著：{item['author']}\n発売日：{sales_date}\n\n▼Amazon\n{amazon_url}"
                send_line(message)
                print(f"✅ ヒット成功: {title} ({new_isbn})")
        else:
            print(f"❌ 最終的にヒットなし: {title}")

    if updated:
        with open('history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
        print("💾 history.json を更新しました。")

def send_line(message):
    if not LINE_NOTIFY_TOKEN: return
    requests.post("https://notify-bot.line.me/api/notify", 
                  headers={"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}, 
                  data={"message": message})

if __name__ == "__main__":
    check_new_manga()
