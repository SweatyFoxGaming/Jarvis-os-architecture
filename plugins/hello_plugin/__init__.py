import logging

logger = logging.getLogger(__name__)

def initialize():
    logger.info("Hello Plugin initialized!")

def shutdown():
    logger.info("Hello Plugin shutting down.")

def health():
    return True
