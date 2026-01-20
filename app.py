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
    # --- デバッグ情報 (ここが重要) ---
    if not RAKUTEN_APP_ID:
        print("❌ 警告: RAKUTEN_APP_ID が設定されていません。")
    else:
        # IDの最初と最後、そして文字数だけを表示して安全に確認
        print(f"📊 デバッグ: 使用中のID={RAKUTEN_APP_ID[:4]}...{RAKUTEN_APP_ID[-4:]} (長さ: {len(RAKUTEN_APP_ID)}文字)")

    if not os.path.exists('history.json'): return
    with open('history.json', 'r', encoding='utf-8') as f:
        history = json.load(f)

    updated = False
    today = datetime.now().strftime('%Y%m%d')

    for title, info in history.items():
        # ヒット率重視：タイトルを簡略化して検索
        search_query = title.split()[0]
        encoded_query = urllib.parse.quote(search_query)
        
        url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?format=json&keyword={encoded_query}&applicationId={RAKUTEN_APP_ID}&booksGenreId=001001"
        
        try:
            res = requests.get(url)
            data = res.json()
            
            # ヒットすれば成功
            if data.get('items'):
                item = data['items'][0]['Item']
                new_isbn = item.get('isbn')
                sales_date = item.get('salesDate')
                
                if str(info.get('isbn')) == "0" or (sales_date and sales_date > info.get('last_notified', '')):
                    history[title]['isbn'] = new_isbn
                    history[title]['salesDate'] = sales_date
                    history[title]['last_notified'] = today
                    updated = True
                    
                    amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                    message = f"\n【新刊】『{item['title']}』\n著：{item['author']}\n発売日：{sales_date}\n{amazon_url}"
                    send_line(message)
                    print(f"✅ ヒット成功: {title}")
            else:
                # ヒットしない場合、楽天からの生のエラーメッセージがあれば出す
                error_msg = data.get('error_description', 'ヒット0件（ID無効の可能性大）')
                print(f"⚠️ 検索失敗({search_query}): {error_msg}")
                
        except Exception as e:
            print(f"‼️ エラー: {e}")

    if updated:
        with open('history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)

def send_line(message):
    if not LINE_NOTIFY_TOKEN: return
    requests.post("https://notify-bot.line.me/api/notify", 
                  headers={"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}, 
                  data={"message": message})

if __name__ == "__main__":
    check_new_manga()
