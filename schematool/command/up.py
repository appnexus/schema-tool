# stdlib imports
from optparse import OptionParser
import os
import sys
from time import time

# local imports
from command import Command
from check import CheckCommand
from constants import Constants
from util import ChainUtil

class UpCommand(Command):
    def init_parser(self):
        usage = "schema up [options] [ref]" \
                "\n\n" \
                "Arguments" \
                "\n  ref               Run all alters up to, and including, the ref given"
        parser = OptionParser(usage=usage)
        parser.add_option('-n', '--number',
                          action='store', dest='N',
                          help='Run N number of up-alters from current state - overrides arguments')
        parser.add_option('-f', '--force',
                          action='store_true', dest='force', default=False,
                          help='Continue running up-alters even if an error has occurred')
        parser.add_option('-v', '--verbose',
                          action='store_true', dest='verbose', default=False,
                          help='Output verbose error-messages when used with -f option if errors are encountered')
        parser.add_option('-u', '--no-undo',
                          action='store_false', dest='undo', default=True,
                          help='When comparing histories (of what has ran and what is to be ran) do not undo ' \
                              'any previously ran alters')
        self.parser = parser

    def run(self):
        """
        Update the DB by checking the current state (stored in the DB itself)
        and and bringing the DB up to date from the current list of alters.

        Returns nothing, but updated DB (via alters) and updated revision number
        in DB table

        Now that we have the history of what has _been_ run and the alter-chain
        of all alters, we can determine what _needs_ to be run. First we will
        go up the history until it diverges with the chain. Then we'll run all
        of the "undos" for any history items that still exist and then run the
        list from where we left off.
        """
        (options, args) = self.parser.parse_args()

        CheckCommand(self.context).run(inline=True)

        # get history
        history = self.db.get_commit_history()
        history = sorted(history, key=lambda h: h[0])
        history_alters = [h[1] for h in history]

        # get current alter-chain
        tail = ChainUtil.build_chain()
        alter_list = [tail]
        if None in alter_list:
            alter_list.remove(None)
        while tail is not None and tail.backref is not None:
            tail = tail.backref
            alter_list.append(tail)

        # find (and remove) synced alters from alter_list (so they are not run again)
        common_history = 0
        for (_id, alter_id, datetime) in history:
            if len(alter_list) == 0:
                break
            alter = alter_list.pop()
            if alter.id == alter_id:
                common_history += 1
            else:
                alter_list.append(alter)
                break

        # undo alters that are not in sync with alter chain if options.undo is true.
        if options.undo:
            uncommon_history = history[common_history:]
            if len(uncommon_history) > 0:
                # clean up alters from here
                uncommon_history.reverse()
                for (_id, alter_id, datetime) in uncommon_history:
                    alters = [a for a in alter_list if a.id == alter_id]
                    if len(alters) > 1:
                        sys.stderr.write("Multiple alters found for a single id (" 
                                + a.id + ")\n")
                        if not options.force:
                            sys.exit(1)
                    alter = alters[0]
                    self.db.run_down(alter)


        # do alters that are in the alter-chain and have not
        # ben run yet
        max = int(options.N or len(alter_list))
        i = 0
        while not len(alter_list) == 0:
            if i == max:
                break

            alter = alter_list.pop()

            if len(args) > 0:
                target_rev = args[0]
                if target_rev == alter.id:
                    i = (max - 1)

            i += 1
            if alter.id not in history_alters:
                self.db.run_up(alter=alter,
                          force=options.force,
                          verbose=options.verbose)
            else:
                sys.stderr.write("Warning: alter " + str(alter.id) + " has already been " \
                        "run. Skipping")

        sys.stdout.write("Updated\n")
