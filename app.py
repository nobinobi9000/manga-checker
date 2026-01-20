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
        # 1月17日と同じ：最初の空白までを抽出
        search_query = title.replace("　", " ").split()[0]
        encoded_query = urllib.parse.quote(search_query)
        
        # 1月17日と全く同じURL構造に戻しました
        url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?format=json&keyword={encoded_query}&applicationId={RAKUTEN_APP_ID}&sort=sales"
        
        try:
            res = requests.get(url)
            data = res.json()
            
            if data.get('Items'):
                item = data['Items'][0]['Item']
                new_isbn = item.get('isbn')
                raw_date = item.get('salesDate', '')
                
                # 比較用数値化
                sales_date_clean = raw_date.replace('年', '').replace('月', '').replace('日', '').replace('頃', '').strip()
                last_notified = str(info.get('last_notified', '0'))
                
                # ISBNが"0"か、新しい日付の場合のみ通知
                if str(info.get('isbn')) == "0" or (sales_date_clean and sales_date_clean > last_notified):
                    history[title]['isbn'] = new_isbn
                    history[title]['salesDate'] = raw_date
                    history[title]['last_notified'] = today
                    updated = True
                    
                    # Amazonリンク作成（楽天から取得したnew_isbnを使用）
                    amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                    message = f"【新刊情報】\n『{item['title']}』\n発売日：{raw_date}\n\n▼Amazon\n{amazon_url}"
                    
                    send_line(message)
                    print(f"✅ 取得成功: {title}")
            else:
                print(f"⚠️ ヒットなし: {search_query}")
                
        except Exception as e:
            print(f"‼️ エラー: {e}")

    if updated:
        with open('history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)

def send_line(message):
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"
    }
    payload = {"messages": [{"type": "text", "text": message}]}
    try:
        requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    except:
        pass

if __name__ == "__main__":
    check_new_manga()
