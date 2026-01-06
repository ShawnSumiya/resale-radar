"""
LINE通知機能モジュール（LINE Messaging API使用）
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError
from utils.logger import get_logger

# プロジェクトルートにある .env を確実に読み込む
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH)

logger = get_logger(__name__)


def send_line_notification(message: str, channel_access_token: Optional[str] = None, user_id: Optional[str] = None) -> bool:
    """
    LINE Messaging APIで通知を送信
    
    Args:
        message: 送信するメッセージ
        channel_access_token: チャネルアクセストークン（未指定の場合は環境変数から取得）
        user_id: ユーザーID（未指定の場合は環境変数から取得）
        
    Returns:
        送信成功時True、失敗時False
    """
    # トークンとユーザーID取得
    if channel_access_token is None:
        channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    
    if user_id is None:
        user_id = os.getenv('LINE_USER_ID')
    
    if not channel_access_token:
        logger.warning("LINE_CHANNEL_ACCESS_TOKENが設定されていません。通知をスキップします。")
        return False
    
    if not user_id:
        logger.warning("LINE_USER_IDが設定されていません。通知をスキップします。")
        return False
    
    try:
        # LineBotApi初期化
        line_bot_api = LineBotApi(channel_access_token)
        
        # プッシュ通知送信
        line_bot_api.push_message(user_id, TextSendMessage(text=message))
        
        logger.debug("LINE通知送信成功")
        return True
        
    except LineBotApiError as e:
        # LINE Messaging APIのエラー（200通制限超過など）
        logger.error(f"LINE送信エラー: {e}")
        logger.error(f"エラー詳細 - status_code: {e.status_code}, message: {e.message}")
        return False
    except Exception as e:
        logger.error(f"LINE通知処理エラー: {e}", exc_info=True)
        return False

