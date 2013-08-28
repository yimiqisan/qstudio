#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成 uwsgi 配置文件并输出到 stdout

"""
import os
import sys
import json

from frame.platform import config


def main():
    try:
        yamlfile = sys.argv[1]
    except IndexError:
        raise Exception('Please provide the path of loading yaml.')
    global_data = config.load_yaml(os.path.join(os.environ['BASE'],
                                                'guokr.yaml'))
    app_data = config.load_yaml(yamlfile)

    chdir = os.path.abspath(os.path.dirname(yamlfile))
    chdir = os.path.relpath(chdir, os.environ['BASE'])

    appname = app_data['APPNAME']
    data = global_data['APP_' + appname.upper()]
    use_http = global_data.get('USE_HTTP')
    data.update(app_data)

    # uwsgi 读取 yaml 时对顺序有要求, 因此使用 json 来 dump
    uwsgi = {
        'master': 1,
        'buffer-size': 32768,
        'so-keepalive': 1,
        'chdir': ('%(base_dir)/' + chdir),
        'pep3333-input': '',
        'post-buffering': 4096,
    }
    if data.get('USE_HTTP', use_http):
        uwsgi['http-socket'] = '%(HOST)s:%(PORT)s' % data
        #uwsgi['protocol'] = 'http'
        #uwsgi['http-keepalive'] = 1
        #uwsgi.setdefault('add-header', []).append('Connection: Keep-Alive')
    else:
        uwsgi['socket'] = '%(HOST)s:%(PORT)s' % data

    if 'MODULE' in data:
        uwsgi['module'] = data['MODULE']
    else:
        uwsgi['module'] = 'app:app'

    if 'ROUTE' in data:
        uwsgi['route'] = data['ROUTE']

    if 'ATTACH_DAEMON' in data:
        uwsgi['attach-daemon'] = data['ATTACH_DAEMON']

    if 'SMART_ATTACH_DAEMON' in data:
        uwsgi['smart-attach-daemon'] = data['SMART_ATTACH_DAEMON']

    if 'SMART_ATTACH_DAEMON2' in data:
        uwsgi['smart-attach-daemon2'] = data['SMART_ATTACH_DAEMON2']

    if 'WORKER_EXEC' in data:
        uwsgi['worker-exec'] = data['WORKER_EXEC']

    if 'PLUGINS' in data:
        uwsgi['plugins-dir'] = '%s/.py/bin' % os.environ['BASE']
        uwsgi['plugins'] = data['PLUGINS']

    if 'JVM_CLASSPATH' in data:
        uwsgi['jvm-classpath'] = data['JVM_CLASSPATH']

    if 'JVM_MAIN_CLASS' in data:
        uwsgi['jvm-main-class'] = data['JVM_MAIN_CLASS']

    if 'DISABLE_LOGGING' in data:
        uwsgi['disable-logging'] = data['DISABLE_LOGGING']

    if 'LISTEN' in data:
        uwsgi['listen'] = data['LISTEN']

    if 'LOG_4XX' in data:
        uwsgi['log-4xx'] = data['LOG_4XX']

    if 'LOG_5XX' in data:
        uwsgi['log-5xx'] = data['LOG_5XX']

    # uwsgi 1.3.1 才支持
    #if 'SMART_ATTACH_DAEMON' in data:
    #    uwsgi['smart-attach-daemon'] = data['SMART_ATTACH_DAEMON']

    if 'PROCESSES' in data:
        uwsgi['processes'] = data['PROCESSES']

    if 'ENABLE_THREADS' in data:
        uwsgi['enable-threads'] = data['ENABLE_THREADS']

    uwsgi['env'] = [
        'GUOKR_APPNAME=%s' % data['APPNAME'],
    ]
    print json.dumps({'uwsgi': uwsgi}),

if __name__ == '__main__':
    main()
