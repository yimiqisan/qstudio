#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
加载 yaml 文件并输出环境变量

"""
import sys

from frame.platform import config


def main():
    try:
        yamlfile = sys.argv[1]
    except IndexError:
        raise Exception('Please provide the path of loading yaml.')
    data = config.load_yaml(yamlfile)
    use_http = data['APP_ROUTER'].get('USE_HTTP', data['USE_HTTP'])
    domain_name = data['DOMAIN_NAME']
    unified_port = data['UNIFIED_PORT']
    subdomains = ['apis', 'services', 'account', 'backends', 'www']

    for subdomain in subdomains:
        k = 'SERVER_' + subdomain.upper()
        if k in data:
            v = data[k]
        else:
            v = '%s.%s' % (subdomain, domain_name)
            if use_http:
                v += ':%s' % unified_port
        print 'export STUDIO_' + k + '=' + v

    print ('export STUDIO_ELASTICSEARCH_DOMAIN=' +
           data['ELASTICSEARCH_DOMAIN'] + ':9200')
    print 'export STUDIO_RABBITMQ=' + data['RABBITMQ']
    print 'export STUDIO_VERSION=%s' % data['VERSION']
    print 'export STUDIO_UNIFIED_PORT=%s' % unified_port

if __name__ == '__main__':
    main()
