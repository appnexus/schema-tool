# stdlib imports
from optparse import OptionParser
import sys

# local imports
from command import Command
from check import CheckCommand
from errors import MissingDownAlterError, MissingRefError, OptionsError
from util import ChainUtil

class DownCommand(Command):
    def init_parser(self):
        usage = "schema down [options] [all|base|ref]" \
                "\n\n" \
                "Arguments" \
                "\n  all               Undo all alters" \
                "\n  base              Undo all but the initial alter" \
                "\n  ref               Undo all previously run alters up to, and including, the ref given"
        parser = OptionParser(usage=usage)
        parser.add_option('-n', '--number',
                          action='store', dest='N',
                          help='Run N number of down-alters from current state - overrides arguments')
        parser.add_option('-f', '--force',
                          action='store_true', dest='force', default=False,
                          help='Continue running down-alters even if an error has occurred')
        parser.add_option('-v', '--verbose',
                          action='store_true', dest='verbose', default=False,
                          help='Output verbose error-messages when used with -f option if errors are encountered')
        self.parser = parser

    def run(self):
        """
        Analogous to what the up_command definition does, but in reverse.
        """
        (options, args) = self.parser.parse_args()

        CheckCommand(self.context).run(inline=True)

        # check validity of options (can't really do this in OptionParser AFAIK)
        if len(args) == 0 and options.N is None:
            raise OptionsError("must specify either argument or number of down-alters to run", self.parser.format_help())

        # get current history
        history = self.db.get_commit_history()
        history = sorted(history, key=lambda h: h[0], reverse=True)

        # get current alter chain
        tail = ChainUtil.build_chain()
        alter_list = [tail]
        if None in alter_list:
            alter_list.remove(None)
        while tail is not None and tail.backref is not None:
            tail = tail.backref
            alter_list.append(tail)

        # parse the args given
        run_type, target_rev = self.parse_args(args)

        # collect the down-alters that we need to run depending on the command line
        # options and arguments that were given
        down_alters_to_run = []
        max_history_len = int(options.N or len(history))
        i = 0
        for (_, alter_id, _) in history:
            if i == max_history_len:
                break
            if run_type == 'base':
                if i == (max_history_len - 1):
                    break
            elif run_type == 'all':
                pass
            else:
                if target_rev == alter_id:
                    i = (max_history_len - 1)

            i += 1
            alters = [a for a in alter_list if a.id == alter_id]
            if len(alters) > 0:
                alter = alters[0]
                down_alters_to_run.append(alter)
            else:
                # error depending on the force and verbose flags (missing alter to run)
                if options.force:
                    sys.stderr.write("Warning: missing alter: %s\n" % alter_id)
                    self.db.remove_commit(ref=alter_id)
                else:
                    raise MissingDownAlterError("missing alter: %s\n" % alter_id)

        # ensure that if a target_revision was specified that one was found in
        # in the list of alters to run (down)
        if (run_type == 'revision' and
              target_rev not in [a.id for a in down_alters_to_run]):
            raise MissingRefError('revision (%s) not found in alters that would be run' % target_rev)

        # run all the down-alters that we have collected
        for alter_to_run in down_alters_to_run:
            self.db.run_down(alter=alter_to_run,
                        force=options.force,
                        verbose=options.verbose)

        sys.stdout.write("Downgraded\n")

    def parse_args(self, args):
        run_type = None
        target_rev = None
        if (len(args) > 0):
            if args[0].lower() == 'all':
                run_type = 'all'
            elif args[0].lower() == 'base':
                run_type = 'base'
            else:
                run_type = 'revision'
                target_rev = args[0]

        return (run_type, target_rev)
