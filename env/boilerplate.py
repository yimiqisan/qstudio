# -*- coding: utf-8

"""
创建新的app需要做的工作：
- 在qstudio/code/apps/下建立新的目录

<appname>
|-- alembic.ini
|-- app.yaml
|-- docs
|-- <appname>
|   |-- apis
|   |   +-- __init__.py
|   |-- backends
|   |   +-- __init__.py
|   |-- frontends
|   |   |-- __init__.py
|   |   |-- assets.py
|   |   |-- views
|   |   |   +-- __init__.py
|   |   |-- statics
|   |   |   |-- coffee
|   |   |   |-- css
|   |   |   |-- img
|   |   |   |-- js
|   |   |   +-- less
|   |   +-- templates
|   |       |-- errors
|   |       |-- layouts
|   |       +-- macros
|   |-- __init__.py
|   |-- models
|   |   +-- __init__.py
|   +-- panel
|       +-- __init__.py
|-- migration
|   |-- env.py
|   |-- README
|   |-- script.py.mako
|   +-- versions
+-- tests
    |-- __init__.py
    |-- apis
    |   +-- __init__.py
    |-- backends
    |   +-- __init__.py
    |-- frontends
    |   +-- __init__.py
    |-- panel
    |   +-- __init__.py
    +-- test_<appname>.py
"""


from __future__ import unicode_literals

import os
import sys

# 全局通用变量
APPNAME = ''
APPPATH = ''

# 使用python dict对象来表示目录结构，控制目录的生成过程
# value为"package"的是python package目录，在目录下添加__init__.py文件
# value为"dir"的是文件夹
# value为"file"的是普通文件
# 如果value为一个dict则是一个包含内容的文件夹
# 如果dict有key "_package" 则该目录也是python package
# alembic 生成的文件和文件夹不在这里处理
# 模式为r"{appname}"，将被appname变量替换

FRONTENDS_TREE = {
    "_package": "",
    "assets.py": "file",
    "views": "package",
    "statics": {
        "coffee": "dir",
        "css": "dir",
        "img": "dir",
        "js": "dir",
        "less": "dir",
    },
    "templates": {
        "errors": "dir",
        "layouts": "dir",
        "macros": "dir",
    },
}


APPTREE = {
    "app.yaml": "file",
    "docs": "dir",
    "{appname}": {
        "_package": "",
        "apis": "package",
        "backends": "package",
        "frontends": FRONTENDS_TREE,
        "models": "package",
        "panel": "package",
    },
    "tests": {
        "_package": "",
        "apis": "package",
        "backends": "package",
        "frontends": "package",
        "panel": "package",
        "test_{appname}.py": "file",
    }
}


APP_YAML_CONTENT = """DEVELOPMENT: &defaults\n    APPNAME: {appname}\n    MODULE: {appname}:app\n    DEBUG: true\n    DEFAULT_SUBDOMAIN: www\n\nSTAGING:\n    <<: *defaults\n\nPRODUCTION:\n    <<: *defaults\n    DEBUG: false\n    MAIL_DEBUG: false\n"""

FLASKAPP_INIT_CONTENT = """# -*- coding: utf-8 -*-\n\nfrom frame.platform.flask import StudioFlask\n\napp=StudioFlask(__name__)\n"""


# 初始化通用的全局变量
def init_environ(appname):
    """
        environ指的是在本模块中使用到的全局变量
        - APPNAME：应用的名称
        - APPPATH：应用的路径
    """
    global APPNAME
    global APPPATH

    APPNAME = appname
    STUDIO_APPS_PATH = os.path.join(os.environ['BASE'], 'frame', 'apps')
    APPPATH = os.path.join(STUDIO_APPS_PATH, appname)


# parse app tree and generate app

def parse_app_tree(parse_path, treeobj):

    create_dir(parse_path, '')

    if "_package" in treeobj.keys():
        init_python_package(parse_path, '')
        treeobj.pop("_package")

    if is_flask_path(parse_path):
        init_flask(parse_path)

    for key, value in treeobj.iteritems():

        if key == "{appname}":
            key = key.format(appname=APPNAME)

        if value == "package":
            init_python_package(parse_path, key)

        elif value == "file":
            if key == 'app.yaml':
                init_app_yaml(parse_path, key)
            else:
                create_file(parse_path, key)

        elif value == "dir":
            create_dir(parse_path, key)

        elif type(value) == dict:
            sub_path = os.path.join(parse_path, key)
            parse_app_tree(sub_path, value)


# 各种初始化函数
def init_python_package(path, name):
    tmp_path = os.path.join(path, name)
    if not os.path.exists(tmp_path):
        os.mkdir(tmp_path)
    init_file = os.path.join(tmp_path, '__init__.py')
    with open(init_file, 'wb') as fobj:
        pass


def is_flask_path(path):
    path_list = path.split('/')
    if path_list[-1] == APPNAME and path_list[-2] == APPNAME:
        return True

    return False


def init_flask(path):

    tmp_path = os.path.join(path, '__init__.py')

    with open(tmp_path, 'wb') as fobj:
        fobj.write(FLASKAPP_INIT_CONTENT)


def create_file(path, name):
    tmp_path = os.path.join(path, name)
    if not os.path.exists(tmp_path):
        with open(tmp_path, 'w') as fobj:
            pass


def init_app_yaml(path, name):
    tmp_path = os.path.join(path, name)
    with open(tmp_path, 'wb') as fobj:
        fobj.write(APP_YAML_CONTENT.format(appname=APPNAME))


def create_dir(path, name):
    tmp_path = os.path.join(path, name)
    if not os.path.exists(tmp_path):
        os.mkdir(tmp_path)


if __name__ == '__main__':

    appname = sys.argv[1]

    init_environ(appname)

    # if app path exists, ignore create process
    if os.path.exists(APPPATH):
        print 'exit'
        sys.exit(0)


    parse_app_tree(APPPATH, APPTREE)
