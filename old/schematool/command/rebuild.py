# stdlib imports
from optparse import OptionParser
import sys

# local imports
from command import Command
from up import UpCommand
from down import DownCommand

class RebuildCommand(Command):
    def init_parser(self):
        usage = "schema rebuild [options]"
        parser = OptionParser(usage=usage)
        parser.add_option('-f', '--force',
                          action='store_true', dest='force', default=False,
                          help='Continue running alters even if an error has occurred')
        parser.add_option('-v', '--verbose',
                          action='store_true', dest='verbose', default=False,
                          help='Output verbose error-messages when used with -f option if errors are encountered')
        self.parser = parser

    def run(self):
        (options, _) = self.parser.parse_args()

        sys.stdout.write("Bringing all the way down\n")
        sys.argv = [sys.argv[0]]
        if options.force:
            sys.argv.append('--force')
        if options.verbose:
            sys.argv.append('--verbose')
        sys.argv.append('all')
        DownCommand(self.context).run()

        sys.stdout.write("\nBringing all the way back up\n")
        sys.argv = [sys.argv[0]]
        if options.force:
            sys.argv.append('--force')
        if options.verbose:
            sys.argv.append('--verbose')
        UpCommand(self.context).run()
