import os
import json
import requests
import urllib.parse
from datetime import datetime

# --- 設定エリア ---
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
LINE_NOTIFY_TOKEN = os.environ.get('LINE_NOTIFY_TOKEN')
AMAZON_TRACKING_ID = "nobinobi9000-22"

def check_new_manga():
    if not os.path.exists('history.json'):
        print("history.jsonが見つかりません。")
        return

    with open('history.json', 'r', encoding='utf-8') as f:
        history = json.load(f)

    updated = False
    today = datetime.now().strftime('%Y%m%d')

    for title, info in history.items():
        # URLエンコードで記号やスペースに対応
        encoded_title = urllib.parse.quote(title)
        url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?format=json&title={encoded_title}&applicationId={RAKUTEN_APP_ID}"
        
        try:
            res = requests.get(url)
            if res.status_code == 200:
                data = res.json()
                if data.get('items'):
                    item = data['items'][0]['Item']
                    new_isbn = item.get('isbn', '0')
                    sales_date = item.get('salesDate', '')
                    last_notified = info.get('last_notified', '')
                    
                    # ISBNが0、または新しい発売日がある場合に更新
                    if str(info.get('isbn')) == "0" or (sales_date and sales_date > last_notified):
                        history[title]['isbn'] = new_isbn
                        history[title]['salesDate'] = sales_date
                        history[title]['last_notified'] = today
                        updated = True
                        
                        amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                        message = (
                            f"\n【新刊・登録情報】\n"
                            f"『{item['title']}』\n"
                            f"著：{item['author']}\n"
                            f"発売日：{sales_date}\n\n"
                            f"▼Amazonで購入・予約\n{amazon_url}"
                        )
                        send_line(message)
                        print(f"成功: {title}")
                else:
                    print(f"検索ヒットなし: {title}")
            else:
                # ここでIDが空だと400エラーになりやすい
                print(f"APIエラー ({res.status_code}): {title}")
                if not RAKUTEN_APP_ID:
                    print("警告: RAKUTEN_APP_ID が空です。Secretsの設定を確認してください。")
        except Exception as e:
            print(f"例外発生 ({title}): {e}")

    if updated:
        with open('history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
        print("history.jsonを保存しました。")
    else:
        print("更新の必要なデータはありませんでした。")

def send_line(message):
    if not LINE_NOTIFY_TOKEN:
        return
    url = "https://notify-bot.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
    payload = {"message": message}
    requests.post(url, headers=headers, data=payload)

if __name__ == "__main__":
    check_new_manga()
