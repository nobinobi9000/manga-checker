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
    # 今日の日付を数値化 (例: 20260120)
    today_num = datetime.now().strftime('%Y%m%d')

    for title_key, info in history.items():
        # 1. 検索ワードの整理
        pure_title = title_key.replace(" 講談社", "").replace("　", " ").split()[0]
        author_name = info.get('author', '')
        # 出版社情報がなければ空文字として扱う
        publisher_config = info.get('publisher', '')
        
        # 2. 楽天ブックス「書籍検索API」へリクエスト
        url = "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
        params = {
            "applicationId": RAKUTEN_APP_ID,
            "format": "json",
            "title": pure_title,
            "author": author_name,
            "sort": "-releaseDate",
            "booksGenreId": "001001", # 漫画(コミック)
            "hits": 15
        }
        # 出版社が指定されている場合のみパラメータに追加
        if publisher_config:
            params["publisherName"] = publisher_config
        
        try:
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            
            # ヒットしない場合の再試行（タイトルをさらに絞る）
            if not data.get('Items') or data.get('count') == 0:
                params["title"] = pure_title[:5]
                res = requests.get(url, params=params, timeout=10)
                data = res.json()

            if data.get('Items'):
                items_list = [entry['Item'] for entry in data['Items']]
                
                legit_items = []
                special_items = []
                exclude_words = ['ポストカード', 'ガイド', 'キャラブック', '画集', 'カレンダー', 'ノベル', 'アニメ']
                priority_exclude = ['特装版', '限定版', '付録', 'セット']

                for item in items_list:
                    item_title = item.get('title', '')
                    if any(w in item_title for w in exclude_words): continue
                    
                    # 著者名チェック
                    target_a = author_name.replace(' ', '').replace('　', '')
                    item_a = item.get('author', '').replace(' ', '').replace('　', '')
                    if target_a not in item_a: continue
                    
                    # 通常版か特装版かを分ける
                    if any(w in item_title for w in priority_exclude):
                        special_items.append(item)
                    else:
                        legit_items.append(item)

                # 通常版を最優先。なければ特装版。
                found_item = legit_items[0] if legit_items else (special_items[0] if special_items else None)

                if not found_item:
                    print(f"⚠️ 条件不一致: {title_key}")
                    continue

                new_isbn = found_item.get('isbn')
                raw_date = found_item.get('salesDate', '')
                current_publisher = found_item.get('publisherName', '')
                
                # 日付から数字以外（「頃」など）を排除
                sales_date_num = "".join(filter(str.isdigit, raw_date))
                
                should_notify = False
                
                # --- 通知判定ロジック ---
                # A. 発売日が不明な場合 → 取りこぼし防止のため通知
                if not sales_date_num:
                    should_notify = True
                # B. 発売日が今日より先（未来）の場合
                elif sales_date_num > today_num:
                    # まだ通知していないISBNであれば通知
                    if str(info.get('isbn')) != new_isbn:
                        should_notify = True
                
                if should_notify:
                    # JSONデータの更新（出版社情報がなければここで埋める）
                    history[title_key]['isbn'] = new_isbn
                    history[title_key]['salesDate'] = raw_date
                    history[title_key]['last_notified'] = sales_date_num if sales_date_num else today_num
                    history[title_key]['publisher'] = current_publisher # 出版社情報を補完
                    updated = True
                    
                    amazon_url = f"https://www.amazon.co.jp/s?k={new_isbn}&tag={AMAZON_TRACKING_ID}"
                    message = f"【新刊予約開始】\n『{found_item['title']}』\n著者：{found_item['author']}\n出版社：{current_publisher}\n発売日：{raw_date}\n\n▼Amazon\n{amazon_url}"
                    
                    send_line(message)
                    print(f"✅ 予約通知: {found_item['title']} ({raw_date})")
                else:
                    # 未来の日付でない（すでに発売されている）場合は更新のみ行う（通知はしない）
                    if str(info.get('isbn')) == "0":
                        history[title_key]['isbn'] = new_isbn
                        history[title_key]['salesDate'] = raw_date
                        history[title_key]['last_notified'] = sales_date_num if sales_date_num else today_num
                        history[title_key]['publisher'] = current_publisher
                        updated = True
                    print(f"⏭️ 既刊のためスキップ: {found_item['title']} ({raw_date})")
                    
            else:
                print(f"❓ ヒットなし: {pure_title}")
                
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
