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
- 直近 12 か月の月次推移チャート（Y軸は金額レンジに応じた自動目盛り）
- 年間サマリー画面
- 口座・カテゴリの追加 / 編集 / 有効・無効切り替え
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
- 管理画面: `http://127.0.0.1:8000/admin/`

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

## 注意点

- `manage.py`、`requirements.txt`、`.env.example` はルートではなく `budgetbook/` 配下にあります
- `.env` がないと起動時にエラーになります
- 口座・カテゴリは削除ではなく有効 / 無効で管理します
- 口座の初期残高、カテゴリの区分は作成後に変更できません
- 外部公開するなら HTTPS と secure cookie 設定が必要です

## ドキュメント

- [docs/01_開発手順ガイド.md](docs/01_%E9%96%8B%E7%99%BA%E6%89%8B%E9%A0%86%E3%82%AC%E3%82%A4%E3%83%89.md)
- [docs/02_ファイル別詳解.md](docs/02_%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E5%88%A5%E8%A9%B3%E8%A7%A3.md)

