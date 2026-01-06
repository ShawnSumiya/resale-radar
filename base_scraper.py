"""
基底スクレイパークラス
全サイト共通の処理を定義し、各サイト固有の実装は継承クラスで行う
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set
from pathlib import Path
import sys
import json
import time
from utils.logger import get_logger
from utils.notify import send_line_notification

logger = get_logger(__name__)


class BaseScraper(ABC):
    """全スクレイパーの基底クラス（Template Method Pattern）"""
    
    def __init__(self, site_name: str, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            site_name: サイト名（例: 'yahoo'）
            config: 設定辞書（keywords, min_price等）
        """
        self.site_name = site_name
        self.config = config
        self.keywords = config.get('keywords', [])
        self.min_price = config.get('min_price', 0)
        self.enabled = config.get('enabled', True)

        # 実行ファイルの場所を取得するロジック
        if getattr(sys, "frozen", False):
            app_path = Path(sys.executable).parent
        else:
            app_path = Path(__file__).parent

        # 既に通知済みの商品IDを保持する履歴ファイル（サイトごと）
        # 履歴ファイルを app_path (exeと同じ場所) に保存する
        self._history_file = app_path / f"{self.site_name}_seen_items.json"
        # キーワードごとに通知済み商品IDを管理
        self._seen_items_by_keyword: Dict[str, Set[str]] = self._load_seen_items()
        
    def run(self) -> None:
        """
        メイン実行メソッド（Template Method）
        各ステップを順次実行し、エラーハンドリングを行う
        """
        if not self.enabled:
            logger.info(f"{self.site_name}: スキップ（無効化されています）")
            return
            
        if not self.keywords:
            logger.warning(f"{self.site_name}: キーワードが設定されていません")
            return
            
        try:
            logger.info(f"{self.site_name}: 監視開始（キーワード: {self.keywords}）")
            
            # 各キーワードで検索
            for keyword in self.keywords:
                try:
                    items = self.search(keyword)
                    seen_items = self._get_seen_items_for_keyword(keyword)

                    # 初回実行（＝このキーワードの履歴がまだない／空）の場合は
                    # 取得した商品を「初期データ」として保存するだけで通知しない
                    if not seen_items:
                        saved_count = 0
                        for item in items:
                            item_id = self.get_item_id(item)
                            if item_id:
                                seen_items.add(item_id)
                                saved_count += 1
                        self._save_seen_items()
                        logger.info(
                            f"{self.site_name}: 初回起動のため、通知をスキップして"
                            f"{saved_count}件の商品をデータベースに登録しました（キーワード: {keyword}）"
                        )
                    else:
                        # 2回目以降：前回までの履歴にない商品だけを「新着」として通知
                        new_items = self.filter_new_items(items, seen_items)
                        
                        if new_items:
                            logger.info(f"{self.site_name}: {len(new_items)}件の新着商品を発見（キーワード: {keyword}）")
                            for item in new_items:
                                self.notify(item)
                                # 通知済みとして記録
                                item_id = self.get_item_id(item)
                                if item_id:
                                    seen_items.add(item_id)
                            # キーワードごとの履歴を永続化
                            self._save_seen_items()
                        else:
                            logger.debug(f"{self.site_name}: 新着商品なし（キーワード: {keyword}）")
                        
                    # リクエスト間隔を空ける（サーバー負荷軽減）
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"{self.site_name}: キーワード '{keyword}' の検索中にエラー: {e}", exc_info=True)
                    continue
                    
        except Exception as e:
            logger.error(f"{self.site_name}: 実行中にエラーが発生: {e}", exc_info=True)

    # =========================
    # 履歴管理（初回判定用）
    # =========================
    def _load_seen_items(self) -> Dict[str, Set[str]]:
        """
        キーワードごとの通知済み商品IDをファイルから読み込む
        """
        if not self._history_file.exists():
            return {}

        try:
            with open(self._history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # JSONから読み込んだリストをセットに変換
            return {k: set(v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"{self.site_name}: 履歴データ読み込みエラー: {e}", exc_info=True)
            return {}

    def _save_seen_items(self) -> None:
        """
        キーワードごとの通知済み商品IDをファイルに保存する
        """
        try:
            serializable = {k: list(v) for k, v in self._seen_items_by_keyword.items()}
            with open(self._history_file, "w", encoding="utf-8") as f:
                json.dump(serializable, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"{self.site_name}: 履歴データ保存エラー: {e}", exc_info=True)

    def _get_seen_items_for_keyword(self, keyword: str) -> Set[str]:
        """
        指定キーワードの通知済み商品IDセットを取得（なければ空セットを作成）
        """
        if keyword not in self._seen_items_by_keyword:
            self._seen_items_by_keyword[keyword] = set()
        return self._seen_items_by_keyword[keyword]
    
    @abstractmethod
    def search(self, keyword: str) -> List[Dict[str, Any]]:
        """
        指定キーワードで商品を検索する（抽象メソッド）
        
        Args:
            keyword: 検索キーワード
            
        Returns:
            商品情報のリスト（各要素は辞書形式）
        """
        pass
    
    @abstractmethod
    def parse(self, html: str) -> List[Dict[str, Any]]:
        """
        HTMLを解析して商品情報を抽出する（抽象メソッド）
        
        Args:
            html: HTML文字列
            
        Returns:
            商品情報のリスト
        """
        pass
    
    @abstractmethod
    def get_item_id(self, item: Dict[str, Any]) -> str:
        """
        商品の一意IDを取得する（抽象メソッド）
        
        Args:
            item: 商品情報辞書
            
        Returns:
            商品ID（文字列）
        """
        pass
    
    def filter_new_items(self, items: List[Dict[str, Any]], seen_items: Set[str]) -> List[Dict[str, Any]]:
        """
        新着商品のみをフィルタリング
        
        Args:
            items: 商品情報のリスト
            seen_items: 既に通知済みの商品IDセット（キーワード単位）
            
        Returns:
            新着商品のリスト
        """
        new_items = []
        for item in items:
            item_id = self.get_item_id(item)
            if item_id and item_id not in seen_items:
                # 最低価格チェック
                price = self.get_price(item)
                if price and price >= self.min_price:
                    new_items.append(item)
        return new_items
    
    def get_price(self, item: Dict[str, Any]) -> int:
        """
        商品の価格を取得（デフォルト実装、必要に応じてオーバーライド）
        
        Args:
            item: 商品情報辞書
            
        Returns:
            価格（整数、取得できない場合は0）
        """
        return item.get('price', 0)
    
    def notify(self, item: Dict[str, Any]) -> None:
        """
        LINE通知を送信
        
        Args:
            item: 商品情報辞書
        """
        try:
            message = self.format_notification_message(item)
            send_line_notification(message)
            logger.info(f"{self.site_name}: 通知送信成功 - {item.get('title', 'N/A')}")
        except Exception as e:
            logger.error(f"{self.site_name}: 通知送信失敗: {e}", exc_info=True)
    
    def format_notification_message(self, item: Dict[str, Any]) -> str:
        """
        通知メッセージをフォーマット（デフォルト実装、必要に応じてオーバーライド）
        
        Args:
            item: 商品情報辞書
            
        Returns:
            フォーマット済みメッセージ
        """
        title = item.get('title', 'タイトル不明')
        price = item.get('price', 0)
        url = item.get('url', '')
        
        return f"""
【{self.site_name.upper()}】新着商品発見！

タイトル: {title}
価格: ¥{price:,}
URL: {url}
"""

