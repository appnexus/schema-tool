# stdlib imports
from optparse import OptionParser
import os
import re
import sys

# local imports
from command import Command
from constants import Constants
from util import ChainUtil

class CheckCommand(Command):
    def init_parser(self):
        usage = "schema check [options]"
        parser = OptionParser(usage=usage)
        parser.add_option('-v', '--verbose',
                          action='store_true', dest='verbose', default=False,
                          help='Enable verbose message output')
        self.parser = parser

    def run(self, inline=False):
        """
        Check that the alter-chain is valid

        """
        # TODO  Check that the alter-chain is in line with the DB (but not necessarily up to date)
        # TODO  Make the verbose flag do something based on previous additions
        # TODO  Add flags to only perform certain checks (as described in the other todos)

        if not inline:
            (options, args) = self.parser.parse_args()

        self.files = ChainUtil.get_alter_files()

        # implicitly check validity of chain (integrety check)
        chain = ChainUtil.build_chain()

        # all other checks
        self.check_abandoned_alters(chain)
        self.check_missing_pair()
        self.check_filenames()

        if not inline:
            print("Everything looks good!\n")

    def check_abandoned_alters(self, chain):
        """
        Check for files that do not exist within the current alter-chain.
        """
        tail = chain
        chain_files = []
        while tail is not None:
            chain_files.append(tail.filename)
            tail = tail.backref

        up_alter = re.compile('-up.sql')
        for file in self.files:
            if up_alter.search(file) is not None:
                if file not in chain_files:
                    sys.stderr.write("File not found within build-chain '%s'\n" % file)
                    sys.exit(1)

    def check_missing_pair(self):
        """
        Check for any alters that have an up, but not a down and vice-versa
        """
        up_alter = re.compile('-up.sql')
        down_alter = re.compile('-down.sql')
        for file in self.files:
            if up_alter.search(file) is not None:
                down_file = up_alter.sub('-down.sql', file)
                if not os.path.exists(os.path.join(Constants.ALTER_DIR, down_file)):
                    sys.stderr.write("No down-file found for '%s', expected '%s'\n" % (
                        file, down_file))
                    sys.exit(1)
            elif down_alter.search(file) is not None:
                up_file = down_alter.sub('-up.sql', file)
                if not os.path.exists(os.path.join(Constants.ALTER_DIR, up_file)):
                    sys.stderr.write("No up-file found for '%s', expected '%s'\n" % (
                        file, up_file))
                    sys.exit(1)

    def check_filenames(self):
        """
        Raise an error to the user and exit if a file fails to meet
        our standards.
        """
        for file in self.files:
            if not self.check_filename(file):
                sys.stderr.write("File does not match standard format: '%s'\n" % file)
                sys.stderr.write("Perhaps you should use the 'new' command to create alter-files\n")
                sys.exit(1)

    def check_filename(self, filename):
        """
        Check that the givenfilename meets our standards.
        """
        return Constants.FILENAME_STANDARD.search(filename) is not None
