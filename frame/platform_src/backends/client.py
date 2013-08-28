# -*- coding: utf-8 -*-
import os
from frame.platform.base import StudioRESTfulAPIClient


def get_netloc():
    return os.environ['STUDIO_SERVER_BACKENDS']


class RESTfulBackendAPIClient(StudioRESTfulAPIClient):
    global_params_handlers = []

client = RESTfulBackendAPIClient(get_netloc)
