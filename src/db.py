#!/usr/bin/env python2.7

# File: db
# Author: Nayef Copty <ncopty@appnexus.com>
# with MySQL pieces extracted from John Murray <jmurray@appnexus.com>

import os
import subprocess
import sys
import re

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    pass

try:
    import mysql.connector
    import mysql.connector.errors as db_errors
except ImportError:
    pass


# TODO: Move connection management to schema.py. Instantiate a connection
# before each run() method and close it at the end, using the DB.conn() method.

class Db(object):
    """
    Do not instantiate directly.
    Contains all the methods related to initialization of the environment that the
    script will be running in.
    """

    @classmethod
    def new(cls, config):
        cls.config = config
        cls.conn_initialized = False

        return cls

    @classmethod
    def init(cls, force=False):
        """
        Make sure that the table to track revisions is there.
        """

        if force:
            sys.stdout.write('Removing existing history')
            cls.drop_revision()

        sys.stdout.write('Creating revision database\n')
        cls.create_revision()
        sys.stdout.write('Creating history table\n')
        cls.create_history()
        sys.stdout.write('DB Initialized\n')

    @classmethod
    def run_up(cls, alter, force=False, verbose=False):
        """
        Run the up-alter against the DB
        """
        sys.stdout.write('Running alter: %s\n' % alter.filename)
        filename = alter.abs_filename()
        cls._run_file(filename=filename, exit_on_error=not force, verbose=verbose)

        cls.append_commit(ref=alter.id)

    @classmethod
    def run_down(cls, alter, force=False, verbose=False):
        """
        Run the down-alter against the DB
        """
        sys.stdout.write('Running alter: %s\n' % alter.down_filename())
        filename = alter.abs_filename(direction='down')
        cls._run_file(filename=filename, exit_on_error=not force, verbose=verbose)

        cls.remove_commit(ref=alter.id)

    @classmethod
    def _run_file(cls, filename, exit_on_error=True, verbose=False):
        command, my_env = cls.run_file_cmd()
        proc = subprocess.Popen(command,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env=my_env)

        script = open(filename)
        out, err = proc.communicate(script.read())
        if err:
            sys.stderr.write("\n----------------------\n")
            sys.stderr.write(out.rstrip())
            sys.stderr.write(err.rstrip())
            sys.stderr.write("\n----------------------\n")
        if not proc.returncode == 0:
            sys.stderr.write('Error')
            if verbose:
                sys.stderr.write("\n----------------------\n")
                sys.stderr.write(out.rstrip())
                sys.stderr.write(err.rstrip())
                sys.stderr.write("\n----------------------\n")
            sys.stderr.write("\n")
            if exit_on_error:
                sys.exit(1)

    @classmethod
    def get_applied_alters(cls):
        results = cls.execute('SELECT alter_hash FROM %s' % cls.full_table_name)
        alters_hashes = [result[0] for result in results]
        return alters_hashes

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
                             'following keys: revision_schema_name, history_table_name\n')
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
            conn = mysql.connector.Connect(user=config['username'],
                                           password=config['password'],
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
               '-u', cls.config['username'],
               '-p%s' % cls.config['password']]
        my_env = None
        return cmd, my_env

class PostgresDb(Db):
    @classmethod
    def new(cls, config):
        super(PostgresDb, cls).new(config)
        if 'revision_schema_name' in cls.config:
            cls.full_table_name = '"%s"."%s"' % (cls.config['revision_schema_name'],
                                                 cls.config['history_table_name'])
        else:
            sys.stderr.write('No schema found in config file. Please add one with the key: '
                             'revision_schema_name')
            sys.exit(1)

        return cls

    @classmethod
    def init_conn(cls):
        try:
          psycopg2
        except NameError:
          sys.stderr.write('Postgres module not found/loaded. Please make sure all dependencies are installed\n')
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
            sys.stderr.write('Psycopg2 execution error: %s\n. Query: %s - Data: %s\n.'
                             % (e.message, query, str(data)))
            sys.exit(1)

    @classmethod
    def drop_revision(cls):
        return cls.execute('DROP SCHEMA IF EXISTS %s' % cls.config['revision_schema_name'])

    @classmethod
    def create_revision(cls):
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
        CONSTRAINT pk_%s__id PRIMARY KEY (id)
        )""" % (cls.full_table_name, cls.config['history_table_name']))

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
                    elif key == 'db_name':
                        conn_string_parts.append('dbname=%s')
                        conn_string_params.append(value)
            conn_string = ' '.join(conn_string_parts) % tuple(conn_string_params)
            conn = psycopg2.connect(conn_string)
        except Exception, e:
            sys.stderr.write('Unable to connect to psql: %s\n' % e.message)
            sys.stderr.write('Ensure that the server is running and you can connect normally\n')
            sys.exit(1)

        return conn

    @classmethod
    def run_file_cmd(cls):
        cmd = ['psql',
               '-h', cls.config['host'],
               '-U', cls.config['username'],
               '-v', 'verbose',
               '-v', 'ON_ERROR_STOP=1',
               '-v', 'schema=%s' % cls.config['schema_name'],
               cls.config['db_name']]
        my_env = None
        if 'password' in cls.config:
            my_env = os.environ.copy()
            my_env['PGPASSWORD'] = cls.config['password']
        return cmd, my_env
