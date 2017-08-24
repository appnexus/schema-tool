# Requires vertica-python driver: https://pypi.python.org/pypi/vertica-python/
# which also requires the psycopg2 driver: https://github.com/psycopg/psycopg2
# stdlib imports
import os

try:
    # Pitfalls:
    # 1 - Returns are in lists, not tuples
    # 2 - Parameters are to be tuples, not lists
    import vertica_python
except ImportError:
    pass

# local imports
from db import Db
from errors import DbError

class VerticaDb(Db):
    DEFAULT_PORT=5433

    @classmethod
    def new(cls, config):
        super(VerticaDb, cls).new(config)
        if 'revision_schema_name' in cls.config:
            cls.history_table_name = cls.config['history_table_name']
            cls.full_table_name = '"%s"."%s"' % (cls.config['revision_schema_name'],
                                                 cls.config['history_table_name'])
        else:
            raise DbError('No schema found in config file. Please add one with the key: '
                          'revision_schema_name')

        return cls

    @classmethod
    def init_conn(cls):
        try:
            vertica_python
        except NameError:
            raise DbError('Vertica module not found/loaded. Please make sure all dependencies are installed\n')

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
            cursor.execute('SET search_path TO %s' % cls.config['schema_name'])
            if data:
                cursor.execute(query, data)
            else:
                cursor.execute(query)
            results = []

            if cursor.rowcount > 0:
                try:
                    results = cursor.fetchall()
                except vertica_python.ProgrammingError, e:
                    raise vertica_python.ProgrammingError(e.message)
            cls.conn.commit()
            return results
        except Exception, e:
            raise DbError('Vertica execution error: %s\n. Query: %s - Data: %s\n.'
                          % (e.message, query, str(data)))

    @classmethod
    def drop_revision(cls):
        return cls.execute('DROP SCHEMA IF EXISTS %s' % cls.config['revision_schema_name'])

    @classmethod
    def create_revision(cls):
        # Executing 'CREATE SCHEMA IF NOT EXISTS' fails if the user does not
        # have schema creation privileges, even if the schema already exists.
        # The correct action is to break this method into two parts: checking
        # if the schema exists, and then creating it only if it does not.
        #
        # The 'IF NOT EXISTS' flag is still used in case the database is
        # created after the existence check but before the CREATE statement.
        check = "SELECT EXISTS(SELECT 1 FROM v_catalog.SCHEMATA WHERE schema_name = %s)"
        result = cls.execute(check, (cls.config['revision_schema_name'],))
        if result[0] == [True]:
            return
        else:
            return cls.execute('CREATE SCHEMA IF NOT EXISTS %s' % cls.config['revision_schema_name'])

    @classmethod
    def get_commit_history(cls):
        return cls.execute('SELECT * FROM %s' % cls.full_table_name)

    @classmethod
    def append_commit(cls, ref):
        return cls.execute('INSERT INTO %s (alter_hash) VALUES (%s)' % (cls.full_table_name, '%s'),
                           (ref,))

    @classmethod
    def get_append_commit_query(cls, ref):
        return "INSERT INTO %s (alter_hash, ran_on) VALUES ('%s', NOW())" % (cls.full_table_name, ref)

    @classmethod
    def remove_commit(cls, ref):
        return cls.execute('DELETE FROM %s WHERE alter_hash = %s' % (cls.full_table_name, '%s'),
                           (ref,))

    @classmethod
    def get_remove_commit_query(cls, ref):
        return "DELETE FROM %s WHERE alter_hash = '%s'" % (cls.full_table_name, ref)

    @classmethod
    def create_history(cls):
        return cls.execute("""CREATE TABLE IF NOT EXISTS %s (
        id auto_increment NOT NULL,
        alter_hash VARCHAR(100) NOT NULL,
        ran_on timestamp NOT NULL DEFAULT current_timestamp,
        CONSTRAINT pk_%s__id PRIMARY KEY (id),
        CONSTRAINT uq_%s__alter_hash UNIQUE (alter_hash)
        )""" % (cls.full_table_name, cls.history_table_name, cls.history_table_name))

    @classmethod
    def conn(cls):
        """
        return the vertica connection handle to the configured server
        """
        config = cls.config
        try:
            conn_driver_dict = {}
            conf_to_driver_map = {'host':'host',
                                  'username':'user',
                                  'password':'password',
                                  'revision_db_name':'database',
                                  'port':'port'}
            for conf_key, conf_value in config.iteritems():
                try:
                    driver_key = conf_to_driver_map[conf_key]
                    driver_value = conf_value

                    # NOTE: Vertica Python driver requires non-unicode strings
                    if isinstance(driver_value, unicode):
                        driver_value = str(driver_value)

                    conn_driver_dict[driver_key] = driver_value

                except KeyError:
                    pass

            conn = vertica_python.connect(conn_driver_dict)
        except Exception, e:
            raise DbError("Cannot connect to Vertica Db: %s\n"
                          "Ensure that the server is running and you can connect normally"
                          % e.message)

        return conn

    @classmethod
    def run_file_cmd(cls, filename):
        """
        return a 3-tuple of strings containing:
            the command to run (list)
            environment variables to be passed to command (dictionary or None)
            data to be piped into stdin (file-like object or None)
        """
        port_number = str(cls.config.get('port', VerticaDb.DEFAULT_PORT))
        cmd = ['/opt/vertica/bin/vsql',
               '-h', cls.config['host'],
               '-U', cls.config['username'],
               '-p', port_number,
               '-v', 'VERBOSITY=verbose',
               '-v', 'AUTOCOMMIT=on',
               '-v', 'ON_ERROR_STOP=on',
               '-v', 'schema=%s' % cls.config['schema_name'],
               cls.config['db_name']]
        my_env = None
        if 'password' in cls.config:
            my_env = os.environ.copy()
            my_env['VSQL_PASSWORD'] = cls.config['password']
        return cmd, my_env, open(filename)
