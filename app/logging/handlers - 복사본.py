import logging
from .formatter import default_formatter

def console_handler():
    handler = logging.StreamHandler()
    handler.setFormatter(default_formatter())
    return handler
