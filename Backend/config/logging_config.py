import logging

def configure_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        encoding="utf-8",
        format = "%(asctime)s - %(levelname)s - %(message)s"
        )