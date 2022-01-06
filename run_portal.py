#!/usr/bin/env python

from portal import app
from portal import log_api
from portal import k8s_api

if __name__ == "__main__":
    logger = log_api.init_logger()
    k8s_api.load_kube_config()
    app.run(host='localhost', ssl_context=('./ssl/server.crt', './ssl/server.key'), port=9874)
