import os
import json
import requests
import urllib.parse
from datetime import datetime
import time

# --- 設定 ---
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID', '').strip()
LINE_NOTIFY_TOKEN = os.environ.get('LINE_NOTIFY_TOKEN', '').strip()
AMAZON_TRACKING_ID = "nobinobi9000-22"

def check_new_manga():
    if not os.path.exists('history.json'):
        print("❌ history.json が見つかりません。")
        return
        
    with open('history.json', 'r', encoding='utf-8') as f:
        history = json.load(f)

    updated = False
    today = datetime.now().strftime('%Y%m%d')

    for title, info in history.items():
        # シンプルに最初の空白までを抽出
        search_query = title.replace("　", " ").split()[0]
        encoded_query = urllib.parse.quote(search_query)
        
        # 楽天API推奨：applicationIdを先頭にし、keywordを確実に認識させる
        url = (
            f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?"
            f"applicationId={RAKUTEN_APP_ID}&"
            f"format=json&"
            f"keyword={encoded_query}&"
            f"sort=sales&"
            f"hits=1"
        )
        
        try:
            # 短時間のスリープでAPIブロックを回避
            time.sleep(1)
            res = requests.get(url)
            data = res.json()
            
            if data.get('Items'):
                item = data['Items'][0]['Item']
                fetched_title = item.get('title', '')
                
                # 【重要】検索ワードが取得タイトルに含まれているか厳密にチェック
                # これにより「ONE PIECE」の誤爆を物理的に遮断します
                if search_query.lower() not in fetched_title.lower():
                    print(f"⚠️ 検索不一致（無視）: {search_query} vs {fetched_title}")
                    continue

                new_isbn = item.get('isbn')
                raw_date = item.get('salesDate', '')
                sales_date_clean = raw_date.replace('年', '').replace('月', '').replace('日', '').replace('頃', '').strip()
                
                last_notified = str(info.get('last_notified', '0'))
                
                # 更新判定（ISBNが0、または新しい日付が見つかった場合）
                if str(info.get('isbn')) == "0" or (sales_date_clean and sales_date_clean > last_notified):
                    history[title]['isbn'] = new_isbn
                    history[title]['salesDate'] = raw_date
                    history[title]['last_notified'] = today
                    updated = True
                    
                    # 楽天から取得した正しいISBNでAmazonリンクを作成
                    amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                    message = f"【新刊情報】\n『{fetched_title}』\n発売日：{raw_date}\n\n▼Amazon\n{amazon_url}"
                    
                    send_line(message)
                    print(f"✅ 正しく取得・通知: {fetched_title}")
            else:
                print(f"⚠️ ヒットなし: {search_query}")
                
        except Exception as e:
            print(f"‼️ エラー ({title}): {e}")

    if updated:
        with open('history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
        print("💾 history.json を正常に更新しました。")

def send_line(message):
    if not LINE_NOTIFY_TOKEN: return
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
