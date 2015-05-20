import os
import tempfile
from datetime import datetime

# third-party imports
try:
    import pyhs2 as hive
    from pyhs2.error import Pyhs2Exception
except ImportError:
    pass

# local imports
from db import Db
from errors import DbError, InitError

class HiveDb(Db):
    DEFAULT_PORT = 10000
    DUMMY_ALTER_REF = '000000000000'
    HIVE_INIT_FILENAME = 'schema_tool_hive_init.tsv'

    @classmethod
    def new(cls, config):
        super(HiveDb, cls).new(config)
        if 'revision_db_name' in cls.config and 'history_table_name' in cls.config:
            cls.db_name = '`%s`' % cls.config['revision_db_name']
            cls.history_table_name = cls.config['history_table_name']
            cls.full_table_name = '`%s`.`%s`' % (cls.config['revision_db_name'],
                                                 cls.config['history_table_name'])
        else:
            raise DbError('No history schema found in config file. Please add values for the '
                          'following keys: revision_db_name, history_table_name\n')

        return cls

    @classmethod
    def init_conn(cls):
        try:
            hive
        except NameError:
            raise DbError('Hive client module not found/loaded. Please make sure all dependencies are installed\n')

        cls.conn = cls.conn()
        cls.cursor = cls.conn.cursor()

        cls.conn_initialized = True
        return cls

    @classmethod
    def execute(cls, query, data=None):
        if not cls.conn_initialized:
            cls.init_conn()

        cursor = cls.cursor
        results = []
        try:
            if data:
                cursor.execute(query % data)
            else:
                cursor.execute(query)

            results = cursor.fetch()
            return results
        except Pyhs2Exception, e:
            raise DbError('Could not query DB. Exception:\n%s\n\nQuery:%s' % (e, query))

    @classmethod
    def drop_revision(cls):
        return cls.execute('DROP DATABASE IF EXISTS %s' % cls.config['revision_db_name'])

    @classmethod
    def create_revision(cls):
        # Executing 'CREATE DATABASE IF NOT EXISTS' fails if the user does not
        # have database creation privileges, even if the database already exists.
        # The correct action is to break this method into two parts: checking
        # if the database exists, and then creating it only if it does not.
        #
        # The 'IF NOT EXISTS' flag is still used in case the database is
        # created after the existence check but before the CREATE statement.
        check = 'SHOW DATABASES LIKE "%s"' % cls.config['revision_db_name']
        results = cls.execute(check)
        if len(results):
            return
        else:
            return cls.execute('CREATE DATABASE IF NOT EXISTS %s' % cls.config['revision_db_name'])

    @classmethod
    def get_commit_history(cls):
        # Omit the placeholder row
        return cls.execute('SELECT * FROM %s WHERE alter_hash != \'%s\'' %
            (cls.full_table_name, cls.DUMMY_ALTER_REF))

    @classmethod
    def get_applied_alters(cls):
        # Omit the placeholder row
        results = cls.execute('SELECT alter_hash FROM %s WHERE alter_hash != \'%s\'' %
            (cls.full_table_name, cls.DUMMY_ALTER_REF))
        alters_hashes = [result[0] for result in results]
        return alters_hashes

    @classmethod
    def append_commit(cls, ref):
        return cls.execute(cls.get_append_commit_query(ref))

    @classmethod
    def get_append_commit_query(cls, ref):
        ran_on = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
        return ("""INSERT OVERWRITE TABLE %s SELECT t.alter_hash, t.ran_on FROM
                   (SELECT alter_hash, ran_on FROM %s UNION ALL
                   SELECT '%s' AS alter_hash, '%s' AS ran_on FROM %s LIMIT 1) t""" %
            (cls.full_table_name, cls.full_table_name, ref, ran_on, cls.full_table_name))

    @classmethod
    def remove_commit(cls, ref):
        return cls.execute(cls.get_remove_commit_query(ref))

    @classmethod
    def get_remove_commit_query(cls, ref):
        return ("""INSERT OVERWRITE TABLE %s SELECT t.alter_hash, t.ran_on FROM %s t
                   WHERE t.alter_hash != '%s'""" % (cls.full_table_name, cls.full_table_name, ref))

    @classmethod
    def create_history(cls):
        create_table_result = cls.execute("""CREATE TABLE IF NOT EXISTS %s (
                                                alter_hash string,
                                                ran_on timestamp
                                            ) ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t'
                                            STORED AS TEXTFILE""" % cls.full_table_name)

        # Check whether table has been bootstrapped with the intial placeholder entry
        results = cls.execute('SELECT * FROM %s WHERE alter_hash = \'%s\'' %
            (cls.full_table_name, cls.DUMMY_ALTER_REF))

        if not results:
            # Create a tab-separated file that will be used to seed the history table, and attempt
            # to load it via Hive
            init_file_path = os.path.join(tempfile.gettempdir(), cls.HIVE_INIT_FILENAME)
            with open(init_file_path, 'w') as f:
                ran_on = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
                f.write('%s\t%s\n' % (cls.DUMMY_ALTER_REF, ran_on))
            os.chmod(init_file_path, 0666)

            try:
                # Since the file was created on the local filesystem and the Hive client will execute
                # the following operation such that all local paths are relative to the Hive server's
                # filesystem, this will only work if the Hive server is running locally.
                # Try to load the file anyway - otherwise, warn the user that this step must be done
                # manually
                cls.execute("LOAD DATA LOCAL INPATH '%s' OVERWRITE INTO TABLE %s" %
                    (init_file_path, cls.full_table_name))
            except DbError, e:
                raise InitError('Unable to initialize history table. If you are pointing to a Hive '
                    'server running on a remote host, please copy the file \'%s\' to the same path '
                    'on the Hive server host and re-run the \'init\' command.\n%s' %
                    (init_file_path, e.message))

        return create_table_result

    @classmethod
    def conn(cls):
        """
        return the hive connection handle to the configured server
        """
        config = cls.config
        try:
            connection = hive.connect(host=config['host'], port=config.get('port', cls.DEFAULT_PORT),
                                      authMechanism='NOSASL', user=config['username'],
                                      password=config['password'])
        except Exception, e:
            raise DbError("Cannot connect to Hive Server: %s\n"
                          "Ensure that the server is running and you can connect normally"
                          % e.message)

        return connection

    @classmethod
    def run_file_cmd(cls):
        port = cls.config.get('port', cls.DEFAULT_PORT)
        jdbc_url = 'jdbc:hive2://%s:%s/default;auth=noSasl' % (cls.config['host'], port)
        # Beeline is the recommended Hive command-line client
        cmd = ['beeline', '-u', jdbc_url,
               '-n', cls.config['username'],
               '-p', cls.config['password']]
        my_env = None
        return cmd, my_env
