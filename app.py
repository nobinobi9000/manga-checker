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

    for title_key, info in history.items():
        # 1. 検索用パラメータの準備
        # 作品名から余計な文字列（講談社など）を除去
        pure_title = title_key.replace(" 講談社", "").replace("　", " ").split()[0]
        author_name = info.get('author', '')
        
        # 2. 楽天ブックス「書籍検索API」の仕様に基づいたリクエスト
        # 総合検索ではなく「書籍検索」専用URLを使用
        url = "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
        params = {
            "applicationId": RAKUTEN_APP_ID,
            "format": "json",
            "title": pure_title,      # タイトルパラメータ
            "author": author_name,    # 著者名パラメータ
            "sort": "-releaseDate",   # 発売日順
            "booksGenreId": "001001", # ジャンルを「漫画(コミック)」に固定
            "hits": 5                 # 候補を絞る
        }
        
        try:
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            
            if data.get('Items'):
                # 検索結果の最初（最新）の1件を取得
                item = data['Items'][0]['Item']
                
                # 特典や公式ガイド、ポストカードなどの「本編以外」を徹底排除する
                # （APIで絞りきれない場合の補助ガード）
                exclude_words = ['ポストカード', 'ガイド', 'キャラブック', '画集', 'カレンダー', 'ノベル', 'アニメ']
                if any(word in item['title'] for word in exclude_words):
                    # もし1件目が関連本なら、2件目以降も探す
                    found_legit = False
                    for entry in data['Items']:
                        tmp_item = entry['Item']
                        if not any(word in tmp_item['title'] for word in exclude_words):
                            item = tmp_item
                            found_legit = True
                            break
                    if not found_legit:
                        print(f"⚠️ 本編と思われる書籍が見つかりませんでした: {title_key}")
                        continue

                new_isbn = item.get('isbn')
                raw_date = item.get('salesDate', '')
                sales_date_clean = raw_date.replace('年', '').replace('月', '').replace('日', '').replace('頃', '').strip()
                last_notified = str(info.get('last_notified', '0'))
                
                # ISBNが"0"（新規追加）または、新しい発売日が検出された場合
                if str(info.get('isbn')) == "0" or (new_isbn != info.get('isbn') and sales_date_clean > last_notified):
                    history[title_key]['isbn'] = new_isbn
                    history[title_key]['salesDate'] = raw_date
                    history[title_key]['last_notified'] = sales_date_clean
                    updated = True
                    
                    amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                    message = f"【新刊情報】\n『{item['title']}』\n著者：{item['author']}\n発売日：{raw_date}\n\n▼Amazon\n{amazon_url}"
                    
                    send_line(message)
                    print(f"✅ 取得成功: {item['title']} (ISBN: {new_isbn})")
            else:
                print(f"❓ ヒットなし: {pure_title} ({author_name})")
                
        except Exception as e:
            print(f"‼️ エラー ({title_key}): {e}")

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
