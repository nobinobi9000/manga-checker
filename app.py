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

    for title_key, info in history.items():
        # 検索ワード：スペースがある場合は最初の単語だけを使う（例：「ブルーロック 講談社」→「ブルーロック」）
        search_query = title_key.replace("　", " ").split()[0]
        encoded_query = urllib.parse.quote(search_query)
        
        # 楽天ブックスの「コミック」ジャンル（001001）を指定して検索
        url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?format=json&title={encoded_query}&applicationId={RAKUTEN_APP_ID}&sort=-releaseDate&booksGenreId=001001"
        
        try:
            res = requests.get(url, timeout=10)
            data = res.json()
            
            if data.get('Items'):
                target_author = info.get('author', '')
                found_item = None
                
                # 検索結果（最大30件）の中から、著者名が一致するものを探す
                for entry in data['Items']:
                    item = entry['Item']
                    # 著者名が含まれているかチェック
                    if target_author in item.get('author', ''):
                        found_item = item
                        break
                
                if not found_item:
                    print(f"⚠️ 著者不一致によりスキップ: {title_key}")
                    continue

                item = found_item
                new_isbn = item.get('isbn')
                raw_date = item.get('salesDate', '')
                
                # 日付の比較
                sales_date_clean = raw_date.replace('年', '').replace('月', '').replace('日', '').replace('頃', '').strip()
                last_notified = str(info.get('last_notified', '0'))
                
                # 通知条件: 初回(ISBNが0) または 新しい発売日が検出された場合
                if str(info.get('isbn')) == "0" or (sales_date_clean and sales_date_clean > last_notified):
                    history[title_key]['isbn'] = new_isbn
                    history[title_key]['salesDate'] = raw_date
                    history[title_key]['last_notified'] = sales_date_clean
                    updated = True
                    
                    amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                    message = f"\n【新刊情報】\n『{item['title']}』\n著者：{item['author']}\n発売日：{raw_date}\n\n▼Amazon\n{amazon_url}"
                    
                    # LINE Notifyへ送信
                    send_line(message)
                    print(f"✅ 通知送信: {item['title']}")
            else:
                print(f"❓ ヒットなし: {search_query}")
                
        except Exception as e:
            print(f"‼️ エラー ({title_key}): {e}")

    if updated:
        with open('history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)

def send_line(message):
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
    payload = {"message": message}
    try:
        requests.post(url, headers=headers, data=payload, timeout=10)
    except:
        pass

if __name__ == "__main__":
    check_new_manga()
