# stdlib imports
from optparse import OptionParser

# local imports
from command import Command

class InitCommand(Command):
    def init_parser(self):
        usage = "schema init [options]"
        parser = OptionParser(usage=usage)
        parser.add_option('-f', '--force',
                          action='store_true', dest='force', default=False,
                          help='Forcibly init the table (wiping all old data)')
        self.parser = parser

    def run(self):
        """
        Initialize everything if this is the first time that the tool has been run
        """
        (options, args) = self.parser.parse_args()
        self.db.init(force=options.force)
