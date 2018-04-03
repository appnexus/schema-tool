import os
import re

class Constants(object):
    ALTER_DIR = os.path.abspath(os.path.curdir) + os.path.sep
    BASE_CONFIG_FILE = os.path.join(os.path.expanduser("~"), '.schema-tool')
    CONFIG_FILE = os.path.join(ALTER_DIR, 'config.json')
    COMMANDS = [
        {'command': 'new',      'handler': 'NewCommand'},
        {'command': 'check',    'handler': 'CheckCommand'},
        {'command': 'list',     'handler': 'ListCommand'},
        {'command': 'up',       'handler': 'UpCommand'},
        {'command': 'down',     'handler': 'DownCommand'},
        {'command': 'rebuild',  'handler': 'RebuildCommand'},
        {'command': 'gen-ref',  'handler': 'GenRefCommand'},
        {'command': 'resolve',  'handler': 'ResolveCommand'},
        {'command': 'init',     'handler': 'InitCommand'},
        {'command': 'gen-sql',  'handler': 'GenSqlCommand'}
    ]
    FILENAME_STANDARD = re.compile('^\d{12}-.+-(up|down)\.sql$')
    ENV_NAME_STANDARD = re.compile('^([a-zA-Z0-9_-]+)$')
    ISSUE_URL = "http://github.com/appnexus/schema-tool/issues"
    VERSION = "0.3.0"
