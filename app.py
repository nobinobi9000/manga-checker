import requests
import json
import os
import time

# --- 設定エリア ---
LINE_TOKEN = os.environ.get("LINE_TOKEN") or "YvZ7nXI77YYo55pNu6ZlCHSWsNda8a8cd+g/wKLk82DvYnjlu3Nk9AD6tCb5X4iPiubShOgQL4YscuRV0wSHJ7HdLLVTRgWlXmQMDG7QIPzaaMoAQCoUjCcuBSygt35dA7NpVfzLuRklr1ns3rWGCQdB04t89/1O/w1cDnyilFU="
RAKUTEN_APP_ID = "1024341657340856332"
HISTORY_FILE = "history.json"

def send_line(message):
    if not LINE_TOKEN or "YvZ7n" not in LINE_TOKEN: return
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    payload = {"messages": [{"type": "text", "text": message}]}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f" (LINE送信エラー: {e}) ", end="")

def check_manga():
    if not os.path.exists(HISTORY_FILE): return

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        history = json.load(f)

    new_history = history.copy()
    updated_any = False

    for title, info in history.items():
        current_author = info.get("author", "")
        # スペースを除去した比較用。検索にもこれを使います
        clean_author = current_author.replace(" ", "").replace("　", "")
        
        print(f"チェック中: {title}...", end=" ", flush=True)
        time.sleep(0.3)
        
        params = {
            "applicationId": RAKUTEN_APP_ID,
            "title": title[:10],
            "author": clean_author, # スペースなしでAPIに投げる
            "booksGenreId": "001001",
            "sort": "-releaseDate",
            "format": "json"
        }
        
        try:
            res = requests.get("https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404", params=params, timeout=10)
            items = res.json().get("Items", [])
            
            if not items:
                # 念のため、authorなしで再検索して自前でチェック（保険）
                del params["author"]
                res = requests.get("https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404", params=params, timeout=10)
                items = res.json().get("Items", [])

            if not items:
                print("× ヒットなし")
                continue

            best_match = None
            for item in items:
                book = item["Item"]
                book_author = book.get("author", "").replace(" ", "").replace("　", "")
                if clean_author and (clean_author in book_author or book_author in clean_author):
                    best_match = book
                    break

            if not best_match:
                print(f"× 作者不一致")
                continue

            b_isbn = str(best_match.get("isbn", ""))
            b_title = best_match.get("title", "")
            b_date = best_match.get("salesDate") or best_match.get("releaseDate") or "不明"

            if str(info.get("isbn")) != b_isbn:
                msg = f"\n【新刊通知】\n{b_title}\n著者: {current_author}\n発売日: {b_date}\n{best_match.get('itemUrl', '')}"
                send_line(msg)
                print(f"◎ 新刊通知済み")
                new_history[title]["isbn"] = b_isbn
                new_history[title]["salesDate"] = b_date
                updated_any = True
            else:
                print(f"・ 更新なし")
                    
        except Exception as e:
            print(f"⚠ 失敗: {e}")

    if updated_any:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(new_history, f, indent=4, ensure_ascii=False)
    print("\nチェック完了。")

if __name__ == "__main__":
    check_manga()