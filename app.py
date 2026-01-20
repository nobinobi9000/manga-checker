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
        print("❌ history.json が見つかりません。")
        return
        
    with open('history.json', 'r', encoding='utf-8') as f:
        history = json.load(f)

    updated = False
    today = datetime.now().strftime('%Y%m%d')

    for title, info in history.items():
        # 【改善】キーワードの精度を上げるため、余計な空白を除去
        search_query = title.replace("　", " ").strip().split()[0]
        encoded_query = urllib.parse.quote(search_query)
        
        # 【最重要】applicationId を keyword よりも先に配置
        # 楽天APIはこの順番が崩れると検索ワードを無視することがあります
        url = (
            f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?"
            f"applicationId={RAKUTEN_APP_ID}&"
            f"format=json&"
            f"keyword={encoded_query}&"
            f"sort=sales&"
            f"hits=1"
        )
        
        try:
            res = requests.get(url)
            data = res.json()
            
            if data.get('Items'):
                item = data['Items'][0]['Item']
                # 取得したタイトルが検索ワードを含んでいるか一応チェック
                if search_query not in item['title'] and "ONE PIECE" in item['title']:
                    print(f"⚠️ 検索失敗の可能性（ONE PIECEを回避）: {search_query}")
                    continue

                new_isbn = item.get('isbn')
                raw_date = item.get('salesDate', '')
                
                sales_date_num = raw_date.replace('年', '').replace('月', '').replace('日', '').replace('頃', '').strip()
                last_notified = str(info.get('last_notified', '0'))
                
                # 更新判定
                if str(info.get('isbn')) == "0" or (sales_date_num and sales_date_num > last_notified):
                    history[title]['isbn'] = new_isbn
                    history[title]['salesDate'] = raw_date
                    history[title]['last_notified'] = today
                    updated = True
                    
                    amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                    message = f"【新刊情報】\n『{item['title']}』\n発売日：{raw_date}\n\n▼Amazon\n{amazon_url}"
                    
                    send_line_messaging_api(message)
                    print(f"✅ 正しく通知: {item['title']}")
            else:
                print(f"⚠️ ヒットなし: {search_query}")
                
        except Exception as e:
            print(f"‼️ エラー ({title}): {e}")

    if updated:
        with open('history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
        print("💾 history.json を保存しました。")

def send_line_messaging_api(message_text):
    if not LINE_NOTIFY_TOKEN: return
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"
    }
    payload = {"messages": [{"type": "text", "text": message_text}]}
    try:
        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        if res.status_code != 200:
            print(f"❌ LINE送信失敗: {res.text}")
    except Exception as e:
        print(f"‼️ LINE通信エラー: {e}")

if __name__ == "__main__":
    check_new_manga()
