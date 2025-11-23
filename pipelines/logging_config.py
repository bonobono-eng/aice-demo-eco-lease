"""ログ設定モジュール"""

import sys
from pathlib import Path
from loguru import logger

# ログディレクトリ作成
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def setup_logging():
    """ログ設定を初期化"""
    # 既存のハンドラをクリア
    logger.remove()

    # コンソール出力（INFO以上）
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )

    # ファイル出力（DEBUG以上、ローテーション付き）
    logger.add(
        LOG_DIR / "app_{time:YYYYMMDD}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8"
    )

    # エラー専用ログ（ERROR以上）
    logger.add(
        LOG_DIR / "error_{time:YYYYMMDD}.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8"
    )

    logger.info("Logging configured: console + file output")
    return logger


# モジュール読み込み時に自動設定
setup_logging()
