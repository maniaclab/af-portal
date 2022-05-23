import logging

def init_logger():
    logger = logging.getLogger()
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        fh = logging.FileHandler('af-portal.log')
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s;%(module)s;%(funcName)s;%(levelname)s;%(message)s")
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        logger.propagate = False
        logger.addHandler(ch)
        logger.addHandler(fh)
    return logger

def get_logger():
    return logging.getLogger()