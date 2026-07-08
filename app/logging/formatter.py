import logging

def default_formatter():
    return logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    )
