import os
import json
import requests
from datetime import datetime

# --- 設定エリア ---
# GitHub ActionsのSecretsから取得
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
LINE_NOTIFY_TOKEN = os.environ.get('LINE_NOTIFY_TOKEN')
# あなたのAmazonトラッキングID
AMAZON_TRACKING_ID = "nobinobi9000-22"

def check_new_manga():
    # history.jsonが存在しない場合は終了
    if not os.path.exists('history.json'):
        print("history.jsonが見つかりません。")
        return

    # history.jsonの読み込み
    with open('history.json', 'r', encoding='utf-8') as f:
        history = json.load(f)

    updated = False
    today = datetime.now().strftime('%Y%m%d')

    # 各作品をループで処理
    for title, info in history.items():
        # 楽天APIで検索（タイトルと出版社などのキーワードで精度アップ）
        search_term = title
        url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?format=json&title={search_term}&applicationId={RAKUTEN_APP_ID}"
        
        try:
            res = requests.get(url)
            if res.status_code == 200:
                data = res.json()
                if data.get('items'):
                    item = data['items'][0]['Item']
                    new_isbn = item.get('isbn', '0')
                    sales_date = item.get('salesDate', '')
                    
                    # 更新条件：
                    # 1. 現在のISBNが"0"である（新規登録時）
                    # 2. または、楽天で見つけた発売日が前回の通知日（last_notified）より新しい
                    last_notified = info.get('last_notified', '')
                    
                    if info.get('isbn') == "0" or (sales_date and sales_date > last_notified):
                        history[title]['isbn'] = new_isbn
                        history[title]['salesDate'] = sales_date
                        history[title]['last_notified'] = today
                        updated = True
                        
                        # Amazonアフィリエイトリンクの作成
                        amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                        
                        # LINE通知メッセージの作成
                        message = (
                            f"\n【新刊・登録情報】\n"
                            f"『{item['title']}』\n"
                            f"著：{item['author']}\n"
                            f"発売日：{sales_date}\n\n"
                            f"▼Amazonで購入・予約\n{amazon_url}"
                        )
                        send_line(message)
                        print(f"通知送信: {title}")
            else:
                print(f"APIエラー ({res.status_code}): {title}")
        except Exception as e:
            print(f"エラー発生 ({title}): {e}")

    # データが更新された場合のみ、history.jsonを書き換える
    if updated:
        with open('history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
        print("history.jsonを更新しました。")
    else:
        print("更新の必要なデータはありませんでした。")

def send_line(message):
    if not LINE_NOTIFY_TOKEN:
        print("LINE_NOTIFY_TOKENが設定されていません。")
        return
    url = "https://notify-bot.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
    payload = {"message": message}
    requests.post(url, headers=headers, data=payload)

if __name__ == "__main__":
    check_new_manga()
