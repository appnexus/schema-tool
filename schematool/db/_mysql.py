# stdlib imports
import os
import sys
import re

try:
    dir_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
    sys.path.append(dir_name)
    import mysql.connector
    import mysql.connector.errors as db_errors
except ImportError, e:
    pass

# Local imports
from db import Db

class MySQLDb(Db):
    @classmethod
    def new(cls, config):
        super(MySQLDb, cls).new(config)

        if 'revision_db_name' in cls.config and 'history_table_name' in cls.config:
            cls.full_table_name = '`%s`.`%s`' % (cls.config['revision_db_name'],
                                                 cls.config['history_table_name'])
            cls.db_name = '`%s`' % cls.config['revision_db_name']
        else:
            sys.stderr.write('No history schema found in config file. Please add values for the '
                             'following keys: revision_db_name, history_table_name\n')
            sys.exit(1)


        return cls


    @classmethod
    def init_conn(cls):
        try:
          mysql
        except NameError:
          sys.stderr.write('MySQL module not found/loaded. Please make sure all dependencies are installed\n')
          sys.exit(1)

        cls.conn = cls.conn()
        cls.cursor = cls.conn.cursor()

        cls.conn_initialized = True
        return cls

    @classmethod
    def execute(cls, query, data=None):
        if not cls.conn_initialized:
            cls.init_conn()
        try:
            cursor = cls.cursor
            if data is not None:
              cursor.execute(query, data)
            else:
              cursor.execute(query)
        except mysql.connector.Error, e:
            sys.stderr.write(query)
            sys.stderr.write('\nCould not query DB: %s\n' % e)
            sys.exit(1)

        try:
          res = cursor.fetchall()
        except mysql.connector.InterfaceError, e:
          res = None
        cls.conn.commit()
        return res

    @classmethod
    def drop_revision(cls):
        return cls.execute('DROP DATABASE IF EXISTS %s' % cls.db_name)

    @classmethod
    def create_revision(cls):
        # Executing 'CREATE DATABASE IF NOT EXISTS' fails if the user does not
        # have database creation privileges, even if the database already
        # exists.  The correct action is to break this method into two parts:
        # checking if the database exists, and then creating it only if it does
        # not.
        #
        # The 'IF NOT EXISTS' flag is still used in case the database is
        # created after the existence check but before the CREATE statement.
        check = "SELECT EXISTS(SELECT 1 FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s)"
        result = cls.execute(check, [cls.config['revision_db_name']])
        if result[0] == (1,):
            return
        else:
            return cls.execute('CREATE DATABASE IF NOT EXISTS %s' % cls.db_name)

    @classmethod
    def get_commit_history(cls):
        return cls.execute('SELECT * FROM %s' % cls.full_table_name)

    @classmethod
    def append_commit(cls, ref):
        return cls.execute('INSERT INTO %s (alter_hash) VALUES (%s)' % (cls.full_table_name, '%s'),
                           [ref])

    @classmethod
    def get_append_commit_query(cls, ref):
        return "INSERT INTO %s (alter_hash, ran_on) VALUES ('%s', NOW())" % (cls.full_table_name, ref)

    @classmethod
    def remove_commit(cls, ref):
        return cls.execute('DELETE FROM %s WHERE alter_hash = %s' % (cls.full_table_name, '%s'),
                           [ref])

    @classmethod
    def get_remove_commit_query(cls, ref):
        return "DELETE FROM %s WHERE alter_hash = '%s'" % (cls.full_table_name, ref)

    @classmethod
    def create_history(cls):
        return cls.execute("""CREATE TABLE IF NOT EXISTS %s (
        `id` int(11) unsigned not null primary key auto_increment,
        `alter_hash` varchar(100) not null,
        `ran_on` timestamp not null
        ) engine=InnoDB
        """ % cls.full_table_name)

    @classmethod
    def conn(cls):
        """
        return the mysql connection handle to the configured server
        """
        config = cls.config
        try:
            if cls.config.get('password'):
                conn = mysql.connector.Connect(user=config['username'],
                                               password=config['password'],
                                               host=config['host'],
                                               port=config['port'])
            else:
                conn = mysql.connector.Connect(user=config['username'],
                                               host=config['host'],
                                               port=config['port'])
        except mysql.connector.InterfaceError, ex:
            sys.stderr.write('Unable to connect to mysql: %s\n' % ex)
            sys.stderr.write('Ensure that the server is running and you can connect normally\n')
            sys.exit(1)
        except mysql.connector.ProgrammingError, ex:
            sys.stderr.write('Could not connect to mysql: %s\n' % ex)
            sys.exit(1)
        except db_errors.DatabaseError, er:
            sys.stderr.write('Could not connect to mysql: %s, %s\n\n' % (er.errno, er.msg))
            if er.errno == -1 and re.compile('.*insecure.*').match(er.msg) is not None:
                # print some instructions on connecting with new mode
                sys.stderr.write("Your MySQL version may be running with old_password compatibility mode."
                                 "\nPlease check your CNF files and if necessary change the setting, restart,"
                                 "\nand create a new-user or update your existing users to use new auth.\n")
            sys.exit(1)

        return conn

    @classmethod
    def run_file_cmd(cls):
        cmd = ['mysql',
               '-h', cls.config['host'],
               '-u', cls.config['username']]
        if cls.config.get('password'):
            cmd.append('-p%s' % cls.config['password'])
        my_env = None
        return cmd, my_env

