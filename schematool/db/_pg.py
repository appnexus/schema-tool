# stdlib imports
import os

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    pass

# local imports
from db import Db
from errors import DbError

class PostgresDb(Db):
    DEFAULT_PORT=5432

    @classmethod
    def new(cls, config):
        super(PostgresDb, cls).new(config)
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
            psycopg2
        except NameError:
            raise DbError('Postgres module not found/loaded. Please make sure all dependencies are installed\n')

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
            # If rowcount == 0, just return None.
            #
            # Note from psycopg2 docs:
            #
            # The rowcount attribute specifies the number of rows that the
            # last execute*() produced (for DQL statements like SELECT) or
            # affected (for DML statements like UPDATE or INSERT).
            #
            # http://initd.org/psycopg/docs/cursor.html
            #
            # Thus, it is possible that fetchone/fetchall will fail despite
            # rowcount being > 0.  That error is caught below and None is
            # returned.
            if cursor.rowcount > 0:
                try:
                    results = cursor.fetchall()
                except psycopg2.ProgrammingError, e:
                    if str(e) != 'no results to fetch':
                        raise psycopg2.ProgrammingError(e.message)
            cls.conn.commit()
            return results
        except Exception, e:
            raise DbError('Psycopg2 execution error: %s\n. Query: %s - Data: %s\n.'
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
        check = "SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname = %s)"
        result = cls.execute(check, [cls.config['revision_schema_name']])
        if result[0] == (True,):
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
        id serial NOT NULL,
        alter_hash VARCHAR(100) NOT NULL,
        ran_on timestamp NOT NULL DEFAULT current_timestamp,
        CONSTRAINT pk_%s__id PRIMARY KEY (id),
        CONSTRAINT uq_%s__alter_hash UNIQUE (alter_hash)
        )""" % (cls.full_table_name, cls.history_table_name, cls.history_table_name))

    @classmethod
    def conn(cls):
        """
        return the postgres connection handle to the configured server
        """
        config = cls.config
        try:
            # conn_string here
            conn_string_parts = []
            conn_string_params = []
            for key, value in config.iteritems():
                # Build connection string based on what is defined in the config
                if value:
                    if key == 'host':
                        conn_string_parts.append('host=%s')
                        conn_string_params.append(value)
                    elif key == 'username':
                        conn_string_parts.append('user=%s')
                        conn_string_params.append(value)
                    elif key == 'password':
                        conn_string_parts.append('password=%s')
                        conn_string_params.append(value)
                    elif key == 'revision_db_name':
                        conn_string_parts.append('dbname=%s')
                        conn_string_params.append(value)
                    elif key == 'port':
                        conn_string_parts.append('port=%s')
                        conn_string_params.append(value)
            conn_string = ' '.join(conn_string_parts) % tuple(conn_string_params)
            conn = psycopg2.connect(conn_string)
        except Exception, e:
            raise DbError("Cannot connect to Postgres Db: %s\n"
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
        port_number = str(cls.config.get('port', PostgresDb.DEFAULT_PORT))
        cmd = ['psql',
               '-h', cls.config['host'],
               '-U', cls.config['username'],
               '-p', port_number,
               '-v', 'verbose',
               '-v', 'ON_ERROR_STOP=1',
               '-v', 'schema=%s' % cls.config['schema_name'],
               cls.config['db_name']]
        my_env = None
        if 'password' in cls.config:
            my_env = os.environ.copy()
            my_env['PGPASSWORD'] = cls.config['password']
        return cmd, my_env, open(filename)
