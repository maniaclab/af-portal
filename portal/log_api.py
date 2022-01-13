import logging

def init_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fh = logging.FileHandler('ciconnect-portal.log')
    fh.setLevel(logging.INFO)
    logger.addHandler(ch)
    logger.addHandler(fh)
    formatter = logging.Formatter("%(asctime)s;%(module)s;%(funcName)s;%(levelname)s;%(message)s")
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    logger.propagate = False
    return logger

def get_logger():
    return logging.getLogger()