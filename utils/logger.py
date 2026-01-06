"""
ログ機能モジュール
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

# ログディレクトリを作成
LOG_DIR = Path(__file__).parent.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# ログファイル名（日付付き）
LOG_FILE = LOG_DIR / f"resale_radar_{datetime.now().strftime('%Y%m%d')}.log"


def get_logger(name: str) -> logging.Logger:
    """
    ロガーを取得
    
    Args:
        name: ロガー名（通常は__name__）
        
    Returns:
        設定済みロガー
    """
    logger = logging.getLogger(name)
    
    # 既にハンドラが設定されている場合はそのまま返す
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # フォーマッター
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソールハンドラ
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # ファイルハンドラ
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

