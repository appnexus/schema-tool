# local imports
from db import MySQLDb, PostgresDb, VerticaDb, MemoryDb
from errors import InvalidDBTypeError

class CommandContext(object):
    """
    Represents everything that a command-class could possibly need to do its
    job. Including (but not limited to):
      config
      DB handles
      VCS extensions (coming soon)
      etc
    """

    @staticmethod
    def via(config):
        """
        Construct a CommandContext from a config and setup all auxillary classes
        for DBs, VCS extensions, etc.
        """
        db = None
        if 'type' in config:
            if config['type'] == 'postgres':
                db = PostgresDb.new(config)
            elif config['type'] == 'mysql':
                db = MySQLDb.new(config)
            elif config['type'] == 'vertica':
                db = VerticaDb.new(config)
            elif config['type'] == 'memory-db':
                db = MemoryDb.new(config)
            else:
                raise InvalidDBTypeError("Invalid database type in config. Only "
                                         "'postgres' and 'mysql' are allowed.")
        else:
            db = MySQLDb.new(config)

        return CommandContext(config, db)

    @staticmethod
    def validate_config(config):
        """
        Given a config, check for the required fields. Return the array
        of errors that are encountered. A valid configuration should return
        an empty array.
        """
        errors = []
        if 'type' not in config:
            errors.append("Missing config value 'type'")
        if 'host' not in config:
            errors.append("Missing config value 'host'")
        if 'revision_db_name' not in config:
            errors.append("Missing config value 'revision_db_name'")
        if 'history_table_name' not in config:
            errors.append("Missing config value 'history_table_name'")

        if 'password' in config and 'username' not in config:
            errors.append("'username' missing when 'password' provided")

        return errors

    def __init__(self, config, DB):
        self.config = config
        self.db = DB
