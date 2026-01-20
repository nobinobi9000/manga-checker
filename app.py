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
        # シンプルな検索ワード（最初の空白まで）
        search_query = title.replace("　", " ").split()[0]
        encoded_query = urllib.parse.quote(search_query)
        
        # 診断ログから判明した、ヒット率が最も高いURL
        url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?format=json&keyword={encoded_query}&applicationId={RAKUTEN_APP_ID}&sort=sales"
        
        try:
            res = requests.get(url)
            data = res.json()
            
            # 【重要】楽天APIの応答は「Items」と大文字で始まります
            if data.get('Items'):
                item = data['Items'][0]['Item']
                new_isbn = item.get('isbn')
                
                # 発売日のクリーンアップ（比較用）
                raw_date = item.get('salesDate', '')
                sales_date_clean = raw_date.replace('年', '').replace('月', '').replace('日', '').replace('頃', '').strip()
                
                last_notified = str(info.get('last_notified', '0'))
                
                # 更新判定
                if str(info.get('isbn')) == "0" or (sales_date_clean and sales_date_clean > last_notified):
                    history[title]['isbn'] = new_isbn
                    history[title]['salesDate'] = raw_date
                    history[title]['last_notified'] = today
                    updated = True
                    
                    amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                    message = f"\n【新刊情報】\n『{item['title']}』\n発売日：{raw_date}\n\n▼Amazon\n{amazon_url}"
                    send_line(message)
                    print(f"✅ 取得成功: {title}")
            else:
                print(f"⚠️ ヒットなし: {search_query}")
                
        except Exception as e:
            print(f"‼️ エラー ({title}): {e}")

    if updated:
        with open('history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
        print("💾 history.json を更新しました。")
    else:
        print("😴 更新が必要なデータはありませんでした。")

def send_line(message):
    if not LINE_NOTIFY_TOKEN: return
    try:
        requests.post("https://notify-bot.line.me/api/notify", 
                      headers={"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}, 
                      data={"message": message})
    except:
        print("❌ LINE通知に失敗しました。")

if __name__ == "__main__":
    check_new_manga()
