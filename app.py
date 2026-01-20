import os
import json
import requests
import urllib.parse
from datetime import datetime

# --- 設定 ---
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID', '').strip()
LINE_NOTIFY_TOKEN = os.environ.get('LINE_NOTIFY_TOKEN', '').strip()
AMAZON_TRACKING_ID = "nobinobi9000-22"

def check_new_manga():
    if not os.path.exists('history.json'):
        return
        
    with open('history.json', 'r', encoding='utf-8') as f:
        history = json.load(f)

    updated = False
    today = datetime.now().strftime('%Y%m%d')

    for title, info in history.items():
        # タイトルと著者名を組み合わせて検索精度を上げる
        author = info.get('author', '')
        search_query = f"{title} {author}".strip()
        encoded_query = urllib.parse.quote(search_query)
        
        # 検索パラメータに「楽天ブックス」かつ「コミック」を指定（booksGenreId=001001）
        url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?format=json&title={encoded_query}&applicationId={RAKUTEN_APP_ID}&sort=-releaseDate&booksGenreId=001001"
        
        try:
            res = requests.get(url, timeout=10)
            data = res.json()
            
            if data.get('Items'):
                # 検索結果を上から見て、タイトルが一致するものを探す
                found_item = None
                for entry in data['Items']:
                    item = entry['Item']
                    # 取得したタイトルに、検索したいマンガ名が含まれているかチェック
                    # (例: 「ブルーロック」が「ブルーロック 32巻」に含まれるか)
                    if title.split()[0] in item['title']:
                        found_item = item
                        break
                
                if not found_item:
                    print(f"⚠️ 検索結果に一致なし（他作品除外）: {title}")
                    continue

                item = found_item
                new_isbn = item.get('isbn')
                raw_date = item.get('salesDate', '')
                
                # 日付の比較用クリーニング
                sales_date_clean = raw_date.replace('年', '').replace('月', '').replace('日', '').replace('頃', '').strip()
                last_notified = str(info.get('last_notified', '0'))
                
                # 通知条件: 初回(ISBNが0) または 新しい発売日が検出された場合
                if str(info.get('isbn')) == "0" or (sales_date_clean and sales_date_clean > last_notified):
                    history[title]['isbn'] = new_isbn
                    history[title]['salesDate'] = raw_date
                    history[title]['last_notified'] = sales_date_clean
                    updated = True
                    
                    amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                    message = f"【新刊情報】\n『{item['title']}』\n著者：{item['author']}\n発売日：{raw_date}\n\n▼Amazon\n{amazon_url}"
                    
                    send_line(message)
                    print(f"✅ 通知送信: {item['title']}")
            else:
                print(f"⚠️ ヒットなし: {title}")
                
        except Exception as e:
            print(f"‼️ エラー ({title}): {e}")

    if updated:
        with open('history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)

def send_line(message):
    # LINE Notify 形式に変更 (もとのコードがBroadcast用だったので修正)
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
    payload = {"message": message}
    try:
        requests.post(url, headers=headers, data=payload, timeout=10)
    except:
        pass

if __name__ == "__main__":
    check_new_manga()
