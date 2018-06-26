import logging

def create_logger(name, format=u'[%(asctime)s][%(levelname)-8s][%(name)-15s][%(funcName)-15s][%(message)s]',
                   level=logging.ERROR):
    formatter = logging.Formatter(format)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger