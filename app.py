import os
import json
import requests
import urllib.parse
from datetime import datetime

# --- 設定 ---
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID', '').strip() # 空白を強制削除
LINE_NOTIFY_TOKEN = os.environ.get('LINE_NOTIFY_TOKEN', '').strip()
AMAZON_TRACKING_ID = "nobinobi9000-22"

def check_new_manga():
    if not os.path.exists('history.json'): return
    with open('history.json', 'r', encoding='utf-8') as f:
        history = json.load(f)

    updated = False
    today = datetime.now().strftime('%Y%m%d')

    for title, info in history.items():
        # 最もヒット率が高い「タイトルのみ」で検索
        # 出版社名などが混ざっているとヒットしないため、最初の10文字程度で検索
        search_query = title.split()[0][:10]
        encoded_query = urllib.parse.quote(search_query)
        
        url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?format=json&keyword={encoded_query}&applicationId={RAKUTEN_APP_ID}&booksGenreId=001001"
        
        try:
            res = requests.get(url)
            data = res.json()
            
            # APIからのエラーメッセージを直接ログに出す（これが重要）
            if res.status_code != 200:
                print(f"❌ 楽天APIエラー({res.status_code}): {data.get('error_description', '不明なエラー')}")
                continue

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
                    print(f"✅ 成功: {title}")
            else:
                print(f"⚠️ ヒットなし({search_query}): IDが正しいか確認してください")
                
        except Exception as e:
            print(f"‼️ システムエラー: {e}")

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
