# BudgetBook

`BudgetBook` は Django + HTMX で作ったローカル運用向けの家計簿アプリです。月次ダッシュボードを中心に、年間サマリー、CSV 出力、口座・カテゴリ管理までをひと通り扱えます。

このリポジトリは「リポジトリのルート」と「Django プロジェクト本体のディレクトリ」が分かれています。実際のアプリ本体は `budgetbook/` 配下にあります。

## リポジトリ構成

```text
budgetbook/
|- README.md                # このファイル（メイン）
|- docs/                    # 補足ドキュメント
`- budgetbook/              # Django プロジェクト本体
   |- manage.py
   |- requirements.txt
   |- .env.example
   |- config/
   |- ledger/
   |- static/
   `- templates/
```

## 主な機能

- 月別の収入・支出・差額表示
- 取引の追加 / 編集 / 削除
- 種別に連動したカテゴリ絞り込み
- 摘要検索、口座フィルタ、カテゴリフィルタ
- 口座残高の表示
- 支出カテゴリ別集計
- 支出構成ページ（月間・年間のカテゴリ別円グラフと割合表示）
- 月次取引の CSV エクスポート
- 当月の日別収支推移チャート（Y軸は金額レンジに応じた自動目盛り）
- 年間サマリー画面
- 口座・カテゴリの追加 / 編集 / 削除 / 有効・無効切り替え
- スマホ向けレスポンシブ対応（iPhone / Pixel 等の縦持ち表示）
- Django 標準認証によるログイン制御
- `seed_budget_data` による初期データ投入

## 動作環境

- Python 3.10 以上
- SQLite

## セットアップ

以降のコマンドはリポジトリルートではなく、`budgetbook/` ディレクトリで実行します。

```bash
cd budgetbook

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

python -m pip install -U pip
python -m pip install -r requirements.txt
```

`.env` を作成します。

```bash
# Windows PowerShell
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

`SECRET_KEY` はランダム値に置き換えてください。

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

初期化と起動:

```bash
python manage.py migrate
python manage.py seed_budget_data
python manage.py createsuperuser
python manage.py runserver
```

ブラウザ:

- アプリ: `http://127.0.0.1:8000/`
- 年間サマリー: `http://127.0.0.1:8000/annual/`
- 支出構成: `http://127.0.0.1:8000/expense-breakdown/`
- 設定: `http://127.0.0.1:8000/settings/`
- 管理画面: `http://127.0.0.1:8000/admin/`（`ADMIN_URL_PATH` で変更可能）

## スマホや別端末から使う場合

`budgetbook/.env` の `ALLOWED_HOSTS` に PC の LAN IP を追加します。

```env
ALLOWED_HOSTS=127.0.0.1,localhost,192.168.1.10
```

そのうえで全インターフェースを listen します。

```bash
python manage.py runserver 0.0.0.0:8000
```

## 初期データ

`python manage.py seed_budget_data` で以下を投入します。

- 口座: 現金 / 普通預金
- 収入カテゴリ: 給与 / 副収入 / 臨時収入
- 支出カテゴリ: 食費 / 日用品 / 住居費 / 水道光熱費 / 通信費 / 交通費 / 医療費 / 娯楽費 / 教育費 / 雑費

## テスト

```bash
cd budgetbook
python manage.py test ledger
```

## バックアップ

重要データは主に次の 2 つです。

- `budgetbook/db.sqlite3`
- `budgetbook/.env`

PowerShell での手動バックアップ例:

```powershell
cd budgetbook
$dir = "backup\$(Get-Date -Format 'yyyy-MM-dd_HHmmss')"
New-Item -ItemType Directory -Path $dir | Out-Null
Copy-Item db.sqlite3 -Destination $dir
```

復元は `runserver` 停止後に `db.sqlite3` を上書きしてください。

## 静的ファイルについて

- Chart.js (v4.5.1) は CDN を使わず `static/vendor/chart.umd.min.js` にローカル配置しています
- チャート関連の JS は `static/js/` に外部ファイルとして配置しています（CSP 導入準備のため inline script を排除済み）
- `DEBUG=False`（WhiteNoise）環境では、CSS や JS を変更したあとに `python manage.py collectstatic --noinput` の実行が必要です
- **WhiteNoise はサーバー起動時にファイル一覧をキャッシュします。** `collectstatic` 実行後は必ず `runserver` を再起動してください
- 古い `runserver` プロセスが残っているとポートが競合します。再起動前に既存プロセスが終了していることを確認してください
- `DEBUG=True` なら Django が `static/` を直接配信するため `collectstatic` は不要です

## セキュリティ

### 常時有効（LAN 運用でも適用）

- `X-Frame-Options: DENY` / `X-Content-Type-Options: nosniff` / `Referrer-Policy: same-origin`
- django-axes によるログイン試行回数制限（デフォルト: 5 回失敗で 30 分ロックアウト）
- 管理画面 URL を環境変数 `ADMIN_URL_PATH` で変更可能（デフォルト `admin/`）
- セッション有効期間を `SESSION_COOKIE_AGE` で設定可能（デフォルト 24 時間）

### 公開モード（`ENABLE_HTTPS=1`）

インターネットに公開する場合は `.env` に `ENABLE_HTTPS=1` を追加してください。以下が有効になります:

- `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` = True
- `SECURE_SSL_REDIRECT` = True
- HSTS（`SECURE_HSTS_SECONDS` デフォルト 1 年、`includeSubDomains`）
- HSTS preload は別途 `ENABLE_HSTS_PRELOAD=1` で明示的に有効化（デフォルト OFF）

LAN 内 HTTP 運用ではこれらは **すべて OFF** です。設定しなければ従来どおり動作します。

### 環境変数一覧

| 変数名 | デフォルト | 説明 |
|---|---|---|
| `ENABLE_HTTPS` | OFF | HTTPS 関連設定を一括有効化 |
| `ENABLE_HSTS_PRELOAD` | OFF | HSTS preload を有効化（`ENABLE_HTTPS=1` 時のみ効果あり） |
| `SECURE_HSTS_SECONDS` | 31536000 | HSTS 有効期間（秒） |
| `CSRF_TRUSTED_ORIGINS` | （空） | CSRF で許可するオリジン（カンマ区切り） |
| `ADMIN_URL_PATH` | `admin/` | 管理画面の URL パス |
| `SESSION_COOKIE_AGE` | 86400 | セッション有効期間（秒） |
| `AXES_FAILURE_LIMIT` | 5 | ログイン失敗許容回数 |
| `AXES_COOLOFF_TIME` | 0.5 | ロックアウト時間（時間単位） |

## 注意点

- `manage.py`、`requirements.txt`、`.env.example` はルートではなく `budgetbook/` 配下にあります
- `.env` がないと起動時にエラーになります
- 口座・カテゴリは削除と有効 / 無効切替の両方に対応します。取引が紐づいている場合は保護により削除できないため、無効化で運用してください
- 口座の初期残高、カテゴリの区分は作成後に変更できません
- 外部公開する場合は `ENABLE_HTTPS=1` を設定し、CSP ヘッダー等の追加対策も検討してください

## ドキュメント

- [docs/01_開発手順ガイド.md](docs/01_%E9%96%8B%E7%99%BA%E6%89%8B%E9%A0%86%E3%82%AC%E3%82%A4%E3%83%89.md) — 開発の流れと設計判断の解説
- [docs/02_ファイル別詳解.md](docs/02_%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E5%88%A5%E8%A9%B3%E8%A7%A3.md) — 各ファイルの役割と実装の詳細
- [docs/03_運用ガイド.md](docs/03_%E9%81%8B%E7%94%A8%E3%82%AC%E3%82%A4%E3%83%89.md) — 開発サーバー運用・トラブルシューティング
