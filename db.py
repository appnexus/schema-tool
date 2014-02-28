#!/usr/bin/env python2.7

# File: db
# Author: Nayef Copty <ncopty@appnexus.com>
# with MySQL pieces extracted from John Murray <jmurray@appnexus.com>

import os
import subprocess
import sys
import re

# TODO: Move connection management to schema.py. Instantiate a connection
# before each run() method and close it at the end, using the DB.conn() method.

class Db(object):
    """
    Do not instantiate directly.
    Contains all the methods related to initialization of the environemnt that the
    script will be running in.
    """
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

    @staticmethod
    def run_up(alter, force=False, verbose=False):
        """
        Run the up-alter against the DB
        """
        sys.stdout.write('Running alter: %s\n' % alter.filename)
        filename = alter.abs_filename()
        Db._run_file(filename=filename, exit_on_error=not force, verbose=verbose)

        Db.append_commit(ref=alter.id)

    @staticmethod
    def run_down(alter, force=False, verbose=False):
        """
        Run the down-alter against the DB
        """
        sys.stdout.write('Running alter: %s\n' % alter.down_filename())
        filename = alter.abs_filename(direction='down')
        Db._run_file(filename=filename, exit_on_error=not force, verbose=verbose)

        Db.remove_commit(ref=alter.id)

    @classmethod
    def _run_file(cls, filename, exit_on_error=True, verbose=False):
        command, my_env = cls.run_file_cmd()
        proc = subprocess.Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=my_env)

        script = open(filename)
        out, err = proc.communicate(script.read())

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


class MySQLDb(Db):
    @classmethod
    def init(cls, config, force=False):
        import mysql.connector
        import mysql.connector.errors as db_errors
        cls.config = config
        cls.conn = cls.conn()
        cls.cursor = cls.conn.cursor()
        cls.full_table_name = '`%s`.`%s`' % (cls.config['revision_db_name'],
                                             cls.config['history_table_name'])
        super(MySQLDb, cls).init(force)

    @classmethod
    def execute(cls, query, data):
        try:
            cursor = cls.cursor
            cursor.execute(query, data)
        except mysql.connector.Error, e:
            sys.stderr.write('Could not query DB: %s\n' % e.errmsglong)
            sys.exit(1)
        cls.conn.commit()
        return cursor.fetchall()

    @classmethod
    def drop_revision(cls):
        return cls.execute('DROP TABLE IF EXISTS %s' % cls.full_table_name)

    @classmethod
    def create_revision(cls):
        return cls.execute('CREATE TABLE IF NOT EXISTS %s' % cls.full_table_name)

    @classmethod
    def get_commit_history(cls):
        return cls.execute('SELECT * FROM %s' % cls.full_table_name)

    @classmethod
    def append_commit(cls, ref):
        return cls.execute('INSERT INTO %s (alter_hash) VALUES (%s)' % (cls.full_table_name, '%s'),
                           ref)

    @classmethod
    def remove_commit(cls, ref):
        return cls.execute('DELETE FROM %s WHERE alter_hash = %s' % (cls.full_table_name, '%s'),
                           ref)

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
    def run_file_cmd(config):
        cmd = ['mysql',
               '-h', config['host'],
               '-u', config['username'],
               '-p %s' % config['password']]
        my_env = None
        return cmd, my_env

class PostgresDb(Db):
    @classmethod
    def init(cls, config, force=False):
        import psycopg2
        import psycopg2.extras
        cls.config = config
        cls.conn = cls.conn()
        cls.cursor = cls.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if 'revision_schema_name' in cls.config:
            cls.full_table_name = '"%s"."%s"' % (cls.config['revision_schema_name'],
                                                 cls.config['history_table_name'])
        else:
            cls.full_table_name = '"%s"' % cls.config['history_table_name']
        super(PostgresDb, cls).init(force)

    @classmethod
    def execute(cls, query, data=None):
        try:
            cursor = cls.cursor
            if data:
                cursor.execute(query, data)
            else:
                cursor.execute(query)
            results = None
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
                except psycopg2.ProgrammingError as e:
                    if str(e) != 'no results to fetch':
                        raise psycopg2.ProgrammingError(e.message)
            cls.conn.commit()
            return results
        except Exception, e:
            sys.stderr.write('Psycopg2 execution error: %s\n' % e.message)
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
                           ref)

    @classmethod
    def remove_commit(cls, ref):
        return cls.execute('DELETE FROM %s WHERE alter_hash = %s' % (cls.full_table_name, '%s',
                                                                     ref))

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
               cls.config['db_name']]
        if 'password' in cls.config:
            my_env = os.environ.copy()
            my_env['PGPASSWORD'] = cls.config['password']
        return cmd, my_env
