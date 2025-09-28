import logging
from src.util.config import get_settings

def get_logger(name:str = __name__):


    conf = get_settings()

    logger = logging.getLogger(name)
    logger.setLevel(conf.LOG_LEVEL)

    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        fh = logging.FileHandler("nuitripilot.log", encoding="utf-8")
        fh.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        logger.addHandler(ch)
        logger.addHandler(fh)

    return logger