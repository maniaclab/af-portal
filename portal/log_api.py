import logging

def init_logger():
    logger = logging.getLogger("ciconnect-portal")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    # ch = logging.StreamHandler()
    # ch.setLevel(logging.INFO)
    fh = logging.FileHandler('ciconnect-portal.log')
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s;%(levelname)s;%(message)s")
    # ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    # logger.addHandler(ch)
    logger.addHandler(fh)
    logger.propagate = False
    return logger

def get_logger():
    logger = logging.getLogger("ciconnect-portal");
    return logger