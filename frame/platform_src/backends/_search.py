# -*- coding: utf-8 -*-

import json

from .client import client

def params_handler(data):
    """
    参数通过json包装
    """
    if 'update_data' in data:
        data['update_data'] = json.dumps(data['update_data'])
    if 'delete_data' in data:
        data['delete_data'] = json.dumps(data['delete_data'])
    return data

client.search.index.update.add_params_handlers(params_handler)

client.search.index.update.set_argspec(lambda update_data=[], delete_data=[], _delay=True: None)
