"""
リセール商品監視ツール - メイン処理
"""
import json
import schedule
import time
import sys
from pathlib import Path
from typing import Dict, Any
from utils.logger import get_logger
from scrapers.yahoo import YahooScraper


# 【追加】実行場所を正しく取得する関数
def get_app_path():
    if getattr(sys, "frozen", False):
        # exe化されている場合、実行ファイルの親ディレクトリを返す
        return Path(sys.executable).parent
    else:
        # 通常実行の場合、このファイルの親ディレクトリを返す
        return Path(__file__).parent


logger = get_logger(__name__)

# 設定ファイル・環境ファイルのパス
CONFIG_FILE = get_app_path() / "config.json"
ENV_FILE = get_app_path() / ".env"


def load_config() -> Dict[str, Any]:
    """
    設定ファイルを読み込む
    
    Returns:
        設定辞書
    """
    try:
        if not CONFIG_FILE.exists():
            logger.error(f"設定ファイルが見つかりません: {CONFIG_FILE}")
            return {}
        
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        logger.info("設定ファイルを読み込みました")
        return config
        
    except json.JSONDecodeError as e:
        logger.error(f"設定ファイルのJSON解析エラー: {e}")
        return {}
    except Exception as e:
        logger.error(f"設定ファイル読み込みエラー: {e}", exc_info=True)
        return {}


def create_scrapers(config: Dict[str, Any]) -> list:
    """
    設定に基づいてスクレイパーインスタンスを作成
    
    Args:
        config: 設定辞書
        
    Returns:
        スクレイパーインスタンスのリスト
    """
    scrapers = []
    
    # Yahoo!オークション
    if 'yahoo' in config and config['yahoo'].get('enabled', False):
        try:
            yahoo_scraper = YahooScraper(config['yahoo'])
            scrapers.append(yahoo_scraper)
            logger.info("Yahoo!オークションスクレイパーを初期化しました")
        except Exception as e:
            logger.error(f"Yahoo!オークションスクレイパーの初期化エラー: {e}", exc_info=True)
    
    # 今後、他のサイト（メルカリ、駿河屋等）をここに追加
    # if 'mercari' in config and config['mercari'].get('enabled', False):
    #     try:
    #         mercari_scraper = MercariScraper(config['mercari'])
    #         scrapers.append(mercari_scraper)
    #     except Exception as e:
    #         logger.error(f"メルカリスクレイパーの初期化エラー: {e}", exc_info=True)
    
    return scrapers


def run_monitoring():
    """
    監視処理を実行
    """
    logger.info("=" * 50)
    logger.info("監視処理を開始します")
    logger.info("=" * 50)
    
    # 設定読み込み
    config = load_config()
    if not config:
        logger.error("設定ファイルが読み込めませんでした。処理を終了します。")
        return
    
    # スクレイパー作成
    scrapers = create_scrapers(config)
    if not scrapers:
        logger.warning("有効なスクレイパーがありません。処理を終了します。")
        return
    
    # 各スクレイパーを実行（エラーが発生しても他のスクレイパーは継続）
    for scraper in scrapers:
        try:
            scraper.run()
        except Exception as e:
            logger.error(f"スクレイパー実行エラー ({scraper.site_name}): {e}", exc_info=True)
            continue
    
    logger.info("監視処理を完了しました")
    logger.info("=" * 50)


def main():
    """
    メイン関数
    """
    logger.info("リセール商品監視ツールを起動しました")
    
    # 初回実行
    run_monitoring()
    
    # 定期実行のスケジュール設定（例: 30分ごと）
    # 設定は必要に応じて変更可能
    schedule.every(30).minutes.do(run_monitoring)
    
    logger.info("定期監視を開始します（30分間隔）")
    logger.info("終了するには Ctrl+C を押してください")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1分ごとにスケジュールをチェック
    except KeyboardInterrupt:
        logger.info("プログラムを終了します")
    except Exception as e:
        logger.error(f"予期しないエラー: {e}", exc_info=True)


if __name__ == '__main__':
    main()

