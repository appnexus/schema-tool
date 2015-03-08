# stdlib imports
from optparse import OptionParser
import sys

# local imports
from command import Command
from check import CheckCommand
from errors import MissingRefError, MultipleDownAltersError, MissingDownAlterError
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

        Now that we have the history of what has _been_ run and the alter chain
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

        # get current alter chain
        tail = ChainUtil.build_chain()
        alter_list = [tail]
        if None in alter_list:
            alter_list.remove(None)
        while tail is not None and tail.backref is not None:
            tail = tail.backref
            alter_list.append(tail)

        # find (and remove) synced alters from alter_list (so they are not run again)
        common_history = 0
        for (_, alter_id, _) in history:
            if len(alter_list) == 0:
                break
            # don't count alters for other env's in common-history
            alter = alter_list.pop()
            while not self.should_run(alter):
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
                for (_, alter_id, _) in uncommon_history:
                    alters = [a for a in alter_list if a.id == alter_id]
                    if len(alters) > 1:
                        msg = "Multiple alters found for a single id (%s)" % alter_id
                        if not options.force:
                            raise MultipleDownAltersError(msg)
                        else:
                            sys.stderr.write(msg + "\n")
                    elif len(alters) == 0:
                        raise MissingDownAlterError("Missing down alter %s" % alter_id)
                    alter = alters[0]
                    self.db.run_down(alter)
                    if alter.id in history_alters:
                        history_alters.remove(alter.id)

        # Ensure that if a target ref was specified that one was found in
        # in the list of alters to run (up)
        if len(alter_list) and len(args) and args[0] not in [a.id for a in alter_list]:
            raise MissingRefError('revision (%s) not found in alters that would be run' % args[0])

        # Do alters that are in the alter chain and have not
        # been run yet
        max_ = int(options.N or len(alter_list))
        i = 0
        while not len(alter_list) == 0:
            if i == max_:
                break

            alter = alter_list.pop()

            if len(args) > 0:
                target_rev = args[0]
                if target_rev == alter.id:
                    i = (max_ - 1)

            i += 1
            if alter.id not in history_alters and self.should_run(alter):
                self.db.run_up(alter=alter,
                          force=options.force,
                          verbose=options.verbose)
            elif not self.should_run(alter):
                # possible to get a skipped alter in the event that it wasn't removed
                # in the common-history code (aka, running new alters)
                pass
            else:
                sys.stderr.write("Warning: alter " + str(alter.id) + " has already been " \
                        "run. Skipping\n")

        sys.stdout.write("Updated\n")

    def should_run(self, alter):
        """
        Given an alter, pull out the meta-data and see if we should be running this
        alter based on the current environment.
        """
        run = True
        config_env = self.config.get('env')
        require_env = getattr(alter, 'require_env', False)
        skip_env = getattr(alter, 'skip_env', False)
        if require_env:
            if config_env not in require_env and config_env is not None:
                run = False
        elif skip_env:
            if config_env in skip_env and config_env is not None:
                run = False

        return run
