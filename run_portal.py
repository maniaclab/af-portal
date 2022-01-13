#!/usr/bin/env python

from portal import app
from portal import logger
from portal import k8s_api

if __name__ == "__main__":
    logger.info("Loading kube config file")
    k8s_api.load_kube_config()
    logger.info("Loaded kube config file")
    app.run(host='localhost', ssl_context=('./ssl/server.crt', './ssl/server.key'), port=9874)
