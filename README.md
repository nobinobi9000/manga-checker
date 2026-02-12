# 📚 マンガ新刊チェッカー

LINEで使えるマンガ新刊通知システム。楽天ブックスAPIとSupabaseを活用し、発売日のカウントダウン通知とAmazonアフィリエイトリンクの自動生成を行います。

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-automated-brightgreen)](https://github.com/features/actions)
[![LINE LIFF](https://img.shields.io/badge/LINE-LIFF-00B900)](https://developers.line.biz/ja/docs/liff/)
[![Supabase](https://img.shields.io/badge/Supabase-Database-3ECF8E)](https://supabase.com/)

---

## 📖 目次

- [✨ 特徴](#-特徴)
- [🏗️ システム構成](#️-システム構成)
- [🚀 セットアップ](#-セットアップ)
- [📱 使い方](#-使い方)
- [🔧 技術スタック](#-技術スタック)
- [📊 データフロー](#-データフロー)
- [🎯 通知タイミング](#-通知タイミング)
- [📁 ファイル構成](#-ファイル構成)
- [🛠️ メンテナンス](#️-メンテナンス)
- [❓ トラブルシューティング](#-トラブルシューティング)
- [📝 ライセンス](#-ライセンス)

---

## ✨ 特徴

### 📅 自動カウントダウン通知
- **30日前、14日前、7日前、本日発売**のタイミングで自動通知
- 発売日が変更された場合も自動検知して通知

### 🖼️ 画像付き通知
- 書籍の表紙画像をサムネイルサイズで表示
- LINEの通知を邪魔しない適切なサイズに最適化

### 🔄 データ更新検知
- ISBNや発売日の変更を自動検知
- 変更内容を明示して通知

### 📱 使いやすいUI
- LINE LIFF アプリで直感的に操作
- マンガ検索、登録、管理が簡単

### 🧺 Amazon・楽天対応
- 通知に自動でAmazon・楽天リンク付

---

## 🏗️ システム構成

```
┌─────────────────────────────────────────────────────────┐
│                    ユーザー操作                          │
│                         ↓                                │
│       LINE LIFF アプリ (GitHub Pages)                   │
│              ├ マンガ検索                                │
│              ├ マイリスト管理                            │
│              └ 予約状況・所有巻数管理                    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Google Apps Script (GAS)                   │
│              ├ 楽天API検索                               │
│              ├ Supabaseデータ操作                        │
│              └ ユーザー操作の処理                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   Supabase Database                      │
│                   manga_list テーブル                    │
└─────────────────────────────────────────────────────────┘
                          ↑
┌─────────────────────────────────────────────────────────┐
│           GitHub Actions (毎日8時実行)                  │
│              ├ 楽天APIで最新情報チェック                │
│              ├ 発売日・ISBN変更検知                      │
│              ├ カウントダウン通知判定                    │
│              └ LINE通知送信（画像付き）                  │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 セットアップ

### 必要なもの

- GitHubアカウント
- LINE Developersアカウント
- Supabaseアカウント
- Google アカウント（GAS用）
- 楽天デベロッパーアカウント

### 1. リポジトリのクローン

```bash
git clone https://github.com/nobinobi9000/manga-checker.git
cd manga-checker
```

### 2. GitHub Secrets の設定

リポジトリの `Settings` > `Secrets and variables` > `Actions` で以下を追加：

| Secret名 | 説明 | 取得方法 |
|----------|------|----------|
| `RAKUTEN_APP_ID` | 楽天アプリケーションID | [楽天デベロッパー](https://webservice.rakuten.co.jp/) |
| `LINE_ACCESS_TOKEN` | LINEチャンネルアクセストークン | [LINE Developers](https://developers.line.biz/) |
| `SUPABASE_URL` | SupabaseプロジェクトURL | Supabaseダッシュボード |
| `SUPABASE_KEY` | Supabase APIキー（anon/public） | Supabaseダッシュボード |

### 3. Supabase テーブル作成

```sql
CREATE TABLE manga_list (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at timestamptz DEFAULT now() NOT NULL,
    user_id text NOT NULL,
    title_key text NOT NULL,
    author text,
    publisher text,
    isbn text,
    sales_date text,
    image_url text,
    is_reserved boolean DEFAULT false NOT NULL,
    last_purchased_vol integer DEFAULT 0 NOT NULL,
    last_notified text
);

CREATE INDEX idx_manga_list_user_id ON manga_list(user_id);
CREATE INDEX idx_manga_list_user_title ON manga_list(user_id, title_key);
CREATE INDEX idx_manga_list_reserved ON manga_list(is_reserved);
```

### 4. Google Apps Script の設定

1. [Google Apps Script](https://script.google.com/) で新規プロジェクト作成
2. `code.gs` の内容をコピー
3. スクリプトプロパティに以下を設定：
   - `RAKUTEN_APP_ID`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
4. ウェブアプリとしてデプロイ
5. デプロイURLを `index.html` の `GAS_API_URL` に設定

### 5. LINE LIFF アプリの設定

1. [LINE Developers](https://developers.line.biz/) でMessaging APIチャネル作成
2. LIFF アプリを追加
3. エンドポイントURLに GitHub Pages の URL を設定
4. LIFF ID を `index.html` の `LIFF_ID` に設定

### 6. GitHub Pages の有効化

1. リポジトリの `Settings` > `Pages`
2. Source: `Deploy from a branch`
3. Branch: `main` / `root`
4. Save

---

## 📱 使い方

### マンガの登録

1. LINEで「マンガ新刊チェッカー」トークルームを開く
2. メニューからLIFFアプリを起動
3. 「マンガ検索」タブで作品名を入力
4. 検索結果から「追加」ボタンをクリック

### マイリストの管理

- **並び替え**: 登録順・名前順・発売日順
- **予約済みに設定**: 通知を停止
- **所有巻数入力**: 何巻まで購入したか記録
- **削除**: リストから削除

### 自動通知

毎日朝8時（日本時間）に自動でチェック：

- 📅 **30日前** - 「あと30日で発売です」
- 📅 **14日前** - 「あと14日で発売です」
- 📅 **7日前** - 「あと7日で発売です」
- 🔥 **本日発売** - 「本日発売です」
- 🌟 **データ更新時** - 「発売日が変更されました」

---

## 🔧 技術スタック

### フロントエンド
- **HTML/CSS/JavaScript**
- **Bulma CSS** - UIフレームワーク
- **LINE LIFF SDK** - LINE内表示・認証

### バックエンド
- **Google Apps Script** - サーバーサイド処理
- **Python 3.13** - 定期通知スクリプト
- **GitHub Actions** - 自動実行環境

### データベース
- **Supabase (PostgreSQL)** - データ保存

### 外部API
- **楽天ブックスAPI** - 書籍情報検索
- **LINE Messaging API** - プッシュ通知

### インフラ
- **GitHub Pages** - フロントエンドホスティング
- **GitHub Actions** - 定期実行（cron）

---

## 📊 データフロー

### ユーザー登録時

```
ユーザー → LIFF → GAS → 楽天API → GAS → Supabase
```

### 定期通知時（毎日8時）

```
GitHub Actions → app.py → Supabase (データ取得)
                    ↓
               楽天API (最新情報)
                    ↓
            変更検知・通知判定
                    ↓
               LINE Push API
                    ↓
        Supabase (データ更新) → ユーザー
```

---

## 🎯 通知タイミング

### 通知ルール

| タイミング | 条件 | 通知内容 |
|-----------|------|----------|
| **データ更新時** | ISBNまたは発売日が変更 | 🌟【新刊情報更新】 + 変更内容 |
| **30日前** | `発売日 - 今日 = 30日` | 📅【30日前】 |
| **14日前** | `発売日 - 今日 = 14日` | 📅【14日前】 |
| **7日前** | `発売日 - 今日 = 7日` | 📅【7日前】 |
| **本日発売** | `発売日 = 今日` | 🔥【本日発売】 |

### 重複通知の防止

- `last_notified` カラムで同日の重複を防止
- データ更新時は `last_notified` に関わらず通知
- `is_reserved = true` の場合は通知スキップ

---

## 📁 ファイル構成

```
manga-checker/
├── .github/
│   └── workflows/
│       └── main.yml              # GitHub Actions設定
├── app.py                         # 定期通知スクリプト
├── index.html                     # LIFF UI
├── requirements.txt               # Python依存関係
├── code.gs                        # Google Apps Script（別リポジトリ）
└── README.md                      # このファイル
```

### 主要ファイルの説明

#### `.github/workflows/main.yml`
GitHub Actionsの定期実行設定。毎日23:00 UTC（日本時間8:00）に `app.py` を実行。

#### `app.py`
定期通知のメインロジック。Supabaseからデータ取得、楽天APIで最新情報チェック、LINE通知送信を担当。

#### `index.html`
LIFF アプリのUI。マンガ検索、登録、マイリスト管理の機能を提供。

#### `code.gs` (別管理)
Google Apps Scriptのコード。ユーザー操作の処理、Supabaseとの連携を担当。

---

## 🛠️ メンテナンス

### ログの確認

#### GitHub Actions
1. リポジトリの `Actions` タブ
2. `Daily Manga Check` を選択
3. 最新の実行結果を確認

#### Google Apps Script
1. GASエディタの「実行数」メニュー
2. エラーログを確認

### データベースのバックアップ

1. Supabaseダッシュボードを開く
2. `Table Editor` > `manga_list`
3. `Export to CSV` でバックアップ
4. 月1回程度の定期バックアップを推奨

### 環境変数の更新

#### GitHub Secrets
```bash
# リポジトリ Settings > Secrets and variables > Actions
# 各Secretを更新
```

#### GAS Script Properties
```javascript
// GASエディタ > プロジェクトの設定 > スクリプト プロパティ
// 各プロパティを更新
```

---

## ❓ トラブルシューティング

### 通知が来ない

**確認項目:**
- [ ] GitHub Actionsが正常に実行されているか
- [ ] `is_reserved` が `false` になっているか
- [ ] `sales_date` が設定されているか
- [ ] LINE_ACCESS_TOKEN が正しいか

**解決方法:**
```bash
# ローカルでテスト実行
export RAKUTEN_APP_ID="YOUR_ID"
export LINE_ACCESS_TOKEN="YOUR_TOKEN"
export SUPABASE_URL="YOUR_URL"
export SUPABASE_KEY="YOUR_KEY"
python app.py
```

### 通知が重複する

**原因:** GASの定期トリガーが残っている

**解決方法:**
1. GASエディタの「トリガー」メニュー
2. すべての定期トリガーを削除
3. GASは「ユーザー操作処理のみ」を担当

### 画像が表示されない

**確認項目:**
- [ ] Supabaseの `image_url` カラムに値があるか
- [ ] URLが `https://` で始まっているか

**解決方法:**
- Supabaseで `image_url` を確認
- 楽天APIのレスポンスを確認

### LIFF アプリが開かない

**確認項目:**
- [ ] LIFF IDが正しいか
- [ ] エンドポイントURLが正しいか
- [ ] GitHub Pagesが有効になっているか

**解決方法:**
```javascript
// index.html の LIFF_ID を確認
const LIFF_ID = "2008959676-hW7rllQ0";  // LINE Developersで確認
```

---

## 📈 今後の拡張案

- [ ] 複数画像対応（カルーセル形式）
- [ ] 通知時間のカスタマイズ
- [ ] 出版社・著者でのフィルタリング
- [ ] 楽天とAmazon両方のリンク表示
- [ ] 既読巻数の管理
- [ ] グループでのリスト共有

---

## 🤝 コントリビューション

プルリクエストを歓迎します！大きな変更の場合は、まずissueを開いて変更内容を議論してください。

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

---

## 📝 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

---

## 👤 作者

**nobinobi9000**

- GitHub: [@nobinobi9000](https://github.com/nobinobi9000)

---

## 🙏 謝辞

- [楽天ブックスAPI](https://webservice.rakuten.co.jp/)
- [LINE Developers](https://developers.line.biz/)
- [Supabase](https://supabase.com/)
- [GitHub Actions](https://github.com/features/actions)
- [Bulma CSS](https://bulma.io/)

---

## 📞 サポート

問題が発生した場合は、[Issue](https://github.com/nobinobi9000/manga-checker/issues) を作成してください。

---

<div align="center">

**⭐ このプロジェクトが役に立ったら、スターをつけていただけると嬉しいです！**

</div>
