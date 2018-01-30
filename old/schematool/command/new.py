# stdlib imports
from optparse import OptionParser
import os
import sys
from time import time

# local imports
from command import Command
from constants import Constants
from errors import WriteError
from util import ChainUtil

class NewCommand(Command):
    def init_parser(self):
        usage = "schema new [options]"
        parser = OptionParser(usage=usage)
        parser.add_option('-f', '--file',
                          dest="filename", action="store",
                          help="The name of the new file")

        self.parser = parser

    def run(self):
        """
        Run the "new" command as if it were its own executable. This means
        processing any options and performing the task of creating a new
        alter file.

        Note: This command assumes a starting point that has been created
        manually (and a working db directory exists)

        Return the node ID of the created files, which is used for testing.
        """
        (options, _) = self.parser.parse_args()

        timestamp = str(round(time() * 10)).replace('.', '')
        filename = timestamp + '-' + (options.filename or '_').replace('.sql', '')

        alter_list_tail = ChainUtil.build_chain()

        if alter_list_tail is not None:
            sys.stdout.write("Parent file:  %s\n" % alter_list_tail.filename)

        up_filename = filename + '-up.sql'
        try:
            alter_file = open(os.path.join(Constants.ALTER_DIR, up_filename), 'w')
            alter_file.write("-- direction: up\n")
            if alter_list_tail is not None:
                alter_file.write("-- backref: %s\n" % alter_list_tail.id)
            alter_file.write("-- ref: %s\n" % timestamp)
            alter_file.write("\n\n\n")
        except OSError, ex:
            raise WriteError("Could not write file '%s'\n\t=>%s" % (os.path.join(Constants.ALTER_DIR, up_filename), ex.message))
        sys.stdout.write("Created file: %s\n" % up_filename)

        down_filename = filename + '-down.sql'
        try:
            alter_file = open(os.path.join(Constants.ALTER_DIR, down_filename), 'w')
            alter_file.write("-- direction: down\n")
            if alter_list_tail is not None:
                alter_file.write("-- backref: %s\n" % alter_list_tail.id)
            alter_file.write("-- ref: %s\n" % timestamp)
            alter_file.write("\n\n\n")
        except OSError, ex:
            raise WriteError("Could not write file '%s'\n\t=>%s" % (os.path.join(Constants.ALTER_DIR, up_filename), ex.message))
        sys.stdout.write("Created file: %s\n" % down_filename)

        return timestamp
