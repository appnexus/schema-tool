# stdlib imports
import sys

# local imports
from db import MySQLDb, PostgresDb

class CommandContext:
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
            else:
                sys.stderr.write("Invalid database type in config. Only \
                                  'postgres' and 'mysql' are allowed.")
                sys.exit(1)
        else:
            db = MySQLDb.new(config)

        return CommandContext(config, db)

    def __init__(self, config, DB):
        self.config = config
        self.db = DB
