# -*- coding: utf-8 -*-
"""monkey patch json"""

import json

def default(o):
    if hasattr(o, '_get_current_object'): # for werkzeug.LocalProxy
        return o._get_current_object()
    elif hasattr(o, '__json_default__'):
        return o.__json_default__()
    else:
        raise TypeError(repr(o) + " is not JSON serializable")
    
def patch():
    json._default_encoder = json.JSONEncoder(
        skipkeys=False,
        ensure_ascii=True,
        check_circular=True,
        allow_nan=True,
        indent=None,
        separators=None,
        encoding='utf-8',
        default=default,
    )
