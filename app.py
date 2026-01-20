import os
import requests

RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID', '').strip()

def debug_rakuten():
    print(f"--- 診断開始 ---")
    print(f"使用ID: {RAKUTEN_APP_ID[:5]}...")

    # テスト1: 誰が検索しても100%ヒットするはずの単語「Python」で全ジャンル検索
    test_url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?format=json&keyword=Python&applicationId={RAKUTEN_APP_ID}"
    
    try:
        res = requests.get(test_url)
        print(f"HTTPステータス: {res.status_code}")
        data = res.json()
        
        if "items" in data:
            print(f"✅ 通信成功: {len(data['items'])} 件ヒットしました。")
            print(f"最初の本: {data['items'][0]['Item']['title']}")
        elif "error" in data:
            print(f"❌ 楽天からの拒絶理由: {data.get('error_description')}")
        else:
            print(f"⚠️ ヒット0件: 楽天側であなたのIDがブロックされているか、海外アクセス制限がかかっています。")
            print(f"生の応答データ: {data}") # ここにヒントが隠れています

    except Exception as e:
        print(f"‼️ 通信エラー: {e}")

if __name__ == "__main__":
    debug_rakuten()
