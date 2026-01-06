# Resale Radar

リセール商品・最新出品通知ツール

指定したキーワードで複数のECサイトを定期的に監視し、新着商品をLINE通知するツールです。

## 機能

- ✅ Yahoo!オークションの監視
- ✅ 新着商品の自動検出
- ✅ LINE Notifyによる通知
- ✅ 拡張可能な設計（新しいサイトを簡単に追加可能）

## 技術スタック

- Python 3.10+
- requests: HTTPリクエスト
- beautifulsoup4: HTML解析
- schedule: 定期実行
- python-dotenv: 環境変数管理

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example`をコピーして`.env`を作成し、LINE Notifyトークンを設定してください。

```bash
cp .env.example .env
```

`.env`ファイルを編集：

```
LINE_NOTIFY_TOKEN=your_line_notify_token_here
```

**LINE Notifyトークンの取得方法：**

1. [LINE Notify](https://notify-bot.line.me/)にアクセス
2. ログイン後、「マイページ」→「トークンを発行する」
3. トークン名を入力（例: "Resale Radar"）
4. 通知を送信したいトークルームを選択
5. 発行されたトークンを`.env`に設定

### 3. 設定ファイルの編集

`config.json`を編集して、監視するキーワードや条件を設定してください。

```json
{
  "yahoo": {
    "enabled": true,
    "keywords": ["Pokemon", "ポケモン"],
    "min_price": 1000
  }
}
```

- `enabled`: 監視の有効/無効
- `keywords`: 検索キーワードのリスト
- `min_price`: 最低価格（この価格以上の商品のみ通知）

## 使用方法

### 実行

```bash
python main.py
```

プログラムは30分ごとに自動的に監視を実行します。終了するには`Ctrl+C`を押してください。

### ログ

ログファイルは`logs/`ディレクトリに保存されます。ファイル名は日付付きです（例: `resale_radar_20240101.log`）。

## 新しいサイトを追加する方法

このツールは拡張可能な設計になっています。新しいECサイトを追加するには、以下の手順に従ってください。

### 1. スクレイパークラスの作成

`scrapers/`ディレクトリに新しいファイルを作成します（例: `scrapers/mercari.py`）。

```python
from base_scraper import BaseScraper
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

class MercariScraper(BaseScraper):
    """メルカリ用スクレイパー"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__('mercari', config)
        # 初期化処理
    
    def search(self, keyword: str) -> List[Dict[str, Any]]:
        """検索処理を実装"""
        # サイト固有の検索ロジック
        pass
    
    def parse(self, html: str) -> List[Dict[str, Any]]:
        """HTML解析処理を実装"""
        # サイト固有のパースロジック
        pass
    
    def get_item_id(self, item: Dict[str, Any]) -> str:
        """商品ID取得処理を実装"""
        # サイト固有のID取得ロジック
        pass
```

### 2. スクレイパーを登録

`scrapers/__init__.py`に新しいスクレイパーを追加：

```python
from scrapers.yahoo import YahooScraper
from scrapers.mercari import MercariScraper

__all__ = ['YahooScraper', 'MercariScraper']
```

### 3. メイン処理に追加

`main.py`の`create_scrapers()`関数に新しいサイトの処理を追加：

```python
def create_scrapers(config: Dict[str, Any]) -> list:
    scrapers = []
    
    # Yahoo!オークション
    if 'yahoo' in config and config['yahoo'].get('enabled', False):
        scrapers.append(YahooScraper(config['yahoo']))
    
    # メルカリ（新規追加）
    if 'mercari' in config and config['mercari'].get('enabled', False):
        scrapers.append(MercariScraper(config['mercari']))
    
    return scrapers
```

### 4. 設定ファイルに追加

`config.json`に新しいサイトの設定を追加：

```json
{
  "yahoo": {
    "enabled": true,
    "keywords": ["Pokemon"],
    "min_price": 1000
  },
  "mercari": {
    "enabled": true,
    "keywords": ["ポケモンカード"],
    "min_price": 500
  }
}
```

これで新しいサイトの監視が可能になります！

## 設計思想

このプロジェクトは**Template Method Pattern**を採用しています。

- `BaseScraper`: 全サイト共通の処理フローを定義
- 各サイト固有のスクレイパー: `BaseScraper`を継承し、抽象メソッドを実装

この設計により：
- 新しいサイトを追加する際は、サイト固有の処理のみを実装すればOK
- 共通処理（通知、ログ、エラーハンドリング）は自動的に利用可能
- コードの重複を最小化

## 注意事項

- **Yahoo!オークション**: 現在実装済み。HTML構造が変更された場合は`scrapers/yahoo.py`の調整が必要です。
- **メルカリ**: 対策が厳しいため、実装時は十分な注意が必要です。必要に応じてSelenium等の使用を検討してください。
- **リクエスト頻度**: サーバーに負荷をかけないよう、リクエスト間隔を適切に設定しています。
- **エラーハンドリング**: 1つのサイトでエラーが発生しても、他のサイトの監視は継続されます。

## トラブルシューティング

### LINE通知が届かない

- `.env`ファイルに`LINE_NOTIFY_TOKEN`が正しく設定されているか確認
- LINE Notifyのトークンが有効か確認
- ログファイルでエラーを確認

### 商品が検出されない

- `config.json`のキーワードが正しいか確認
- `min_price`の設定が高すぎないか確認
- ログファイルで検索結果を確認

### HTML解析エラー

- サイトのHTML構造が変更された可能性があります
- `scrapers/`内の該当スクレイパーの`parse()`メソッドを調整してください

## ライセンス

このプロジェクトはココナラ等のスキルマーケットで販売するためのMVPです。

## 今後の拡張予定

- [ ] メルカリ対応
- [ ] 駿河屋対応
- [ ] データベースによる通知履歴管理
- [ ] Web UIの追加
- [ ] 複数キーワードの組み合わせ検索

