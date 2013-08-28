# -*- coding: utf-8 -*-

from .client import client
#from . import _search

def setup():
    from ..base import APIClientImporter
    importer = APIClientImporter(__name__, client)
    importer.install()

setup()
del setup
