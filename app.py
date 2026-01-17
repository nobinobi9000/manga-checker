import os
import json
import requests
from datetime import datetime

# --- 設定エリア ---
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
LINE_NOTIFY_TOKEN = os.environ.get('LINE_NOTIFY_TOKEN')
# あなたのAmazonトラッキングID
AMAZON_TRACKING_ID = "nobinobi9000-22"

def check_new_manga():
    if not os.path.exists('history.json'):
        return

    with open('history.json', 'r', encoding='utf-8') as f:
        history = json.load(f)

    updated = False
    today = datetime.now().strftime('%Y%m%d')

    for title, info in history.items():
        # ISBNが未取得(0)の場合、または発売日が今日以降の新刊を探す
        search_term = title
        url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?format=json&title={search_term}&applicationId={RAKUTEN_APP_ID}"
        
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            if data['items']:
                item = data['items'][0]['Item']
                new_isbn = item['isbn']
                sales_date = item['salesDate']
                
                # 未登録のISBNが見つかった場合、または新刊フラグが立っている場合
                if info.get('isbn') == "0" or (info.get('salesDate') and info['salesDate'] > info.get('last_notified', '')):
                    history[title]['isbn'] = new_isbn
                    history[title]['salesDate'] = sales_date
                    history[title]['last_notified'] = today
                    updated = True
                    
                    # Amazonアフィリエイトリンクの作成（ISBN検索を利用）
                    amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                    
                    # LINE通知メッセージ
                    message = f"\n【新刊・登録情報】\n『{item['title']}』\n著：{item['author']}\n発売日：{sales_date}\n\n▼Amazonで購入・予約\n{amazon_url}"
                    send_line(message)

    if updated:
        with open('history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)

def send_line(message):
    url = "https://notify-bot.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
    payload = {"message": message}
    requests.post(url, headers=headers, data=payload)

if __name__ == "__main__":
    check_new_manga()
