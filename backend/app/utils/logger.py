"""One logging setup for the API, the agent and the news bot: console plus a
rotating file in logs/."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def setup_logging(logs_dir: Path, level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return  # already configured (tests, uvicorn reload)
    logs_dir.mkdir(parents=True, exist_ok=True)
    root.setLevel(level)
    formatter = logging.Formatter(FORMAT)

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    root.addHandler(stream)

    file = RotatingFileHandler(logs_dir / "monsterbroker.log", maxBytes=2_000_000, backupCount=3,
                               encoding="utf-8")
    file.setFormatter(formatter)
    root.addHandler(file)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
