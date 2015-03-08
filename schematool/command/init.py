# stdlib imports
import os
import sys
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

    def _setup_pre_commit_hook(self):
        """
        Copy the pre-commit hook found at config.pre_commit_hook to the
        closest .git directory.  If no .git directory exists, throw an
        exception.
        """
        if self.config.get('pre_commit_hook') is None:
            return

        check_dir = os.getcwd()
        while 1:
            if os.path.exists(os.path.join(check_dir, '.git')):
                break
            elif os.path.normpath(check_dir) == '/':
                raise Exception("No .git directory found for pre-commit hook")
            else:
                # Go up one level
                check_dir = os.path.join(check_dir, os.pardir)

        hook_path = os.path.join(os.getcwd(), self.config['pre_commit_hook'])
        source = os.path.join(hook_path)
        dest = os.path.join(check_dir, '.git', 'hooks', 'pre-commit')

        sys.stdout.write("Setup git pre-commit hook: \n\t%s\n\t-> %s\n" % (dest, source))
        try:
            if os.readlink(dest) == source:
                return
            else:
                os.unlink(dest)
        except OSError:
            pass

        os.symlink(source, dest)

    def run(self):
        """
        Initialize everything if this is the first time that the tool has been run
        """
        (options, _) = self.parser.parse_args()
        self.db.init(force=options.force)
        self._setup_pre_commit_hook()
