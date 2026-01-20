import os
import json
import requests
import urllib.parse
import re
from datetime import datetime

# --- 設定 ---
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')
LINE_NOTIFY_TOKEN = os.environ.get('LINE_NOTIFY_TOKEN')
AMAZON_TRACKING_ID = "nobinobi9000-22"

def clean_text(text):
    """出版社名やカッコを取り除き、検索精度を上げる"""
    if not text: return ""
    # カッコ（全角・半角）とその中身を削除
    text = re.sub(r'（.*?）|\(.*?\)|［.*?］|\[.*?\]', '', text)
    # 主要な出版社名を削除（これらが混ざるとヒットしないため）
    keywords = ["講談社", "集英社", "小学館", "KADOKAWA", "白泉社", "秋田書店", "新潮社", "スクウェア・エニックス"]
    for k in keywords:
        text = text.replace(k, "")
    return text.strip()

def check_new_manga():
    if not os.path.exists('history.json'):
        print("Error: history.json がリポジトリ内に見つかりません。")
        return

    with open('history.json', 'r', encoding='utf-8') as f:
        history = json.load(f)

    updated = False
    today = datetime.now().strftime('%Y%m%d')

    for title, info in history.items():
        # 作品名と著者名を抽出してクリーンアップ
        pure_title = clean_text(title)
        pure_author = clean_text(info.get('author', ''))
        
        # 「作品名 著者名」の形式で検索ワードを作成
        search_query = f"{pure_title} {pure_author}".strip()
        encoded_query = urllib.parse.quote(search_query)
        
        # 楽天APIへのリクエスト（ジャンルを漫画 001001 に固定）
        url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?format=json&title={encoded_query}&applicationId={RAKUTEN_APP_ID}&booksGenreId=001001"
        
        try:
            res = requests.get(url)
            if res.status_code == 200:
                data = res.json()
                if data.get('items'):
                    item = data['items'][0]['Item']
                    new_isbn = item.get('isbn', '0')
                    sales_date = item.get('salesDate', '')
                    
                    # ISBNが "0" の場合、または新しい発売日がある場合に更新
                    current_isbn = str(info.get('isbn', '0'))
                    last_notified = info.get('last_notified', '')
                    
                    if current_isbn == "0" or (sales_date and sales_date > last_notified):
                        history[title]['isbn'] = new_isbn
                        history[title]['salesDate'] = sales_date
                        history[title]['last_notified'] = today
                        updated = True
                        
                        # Amazonリンク作成とLINE通知
                        amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                        message = f"\n【新刊情報】\n『{item['title']}』\n著：{item['author']}\n発売日：{sales_date}\n\n▼Amazon\n{amazon_url}"
                        send_line(message)
                        print(f"✅ 取得成功: {title} (ISBN: {new_isbn})")
                else:
                    print(f"⚠️ 検索結果 0件: {search_query}")
            else:
                print(f"❌ 楽天APIエラー({res.status_code}): {title}")
        except Exception as e:
            print(f"‼️ システムエラー: {e}")

    # 更新があった場合のみ上書き保存
    if updated:
        with open('history.json', 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
        print("💾 history.json を更新しました。")
    else:
        print("😴 更新が必要なデータはありませんでした。")

def send_line(message):
    if not LINE_NOTIFY_TOKEN: return
    requests.post("https://notify-bot.line.me/api/notify", 
                  headers={"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"} , 
                  data={"message": message})

if __name__ == "__main__":
    check_new_manga()
