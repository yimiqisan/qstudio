# -*- coding: utf-8 -*-

from .client import client
from .client import confidential_client as c_client
from . import _auth

def setup():
    from ..base import APIClientImporter
    importer = APIClientImporter(__name__, client, confidential=c_client)
    importer.install()

setup()
del setup
