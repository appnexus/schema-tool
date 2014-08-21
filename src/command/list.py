# stdlib imports
from optparse import OptionParser
import os
import sys

# local imports
from command import Command
from constants import Constants
from util import ChainUtil

class ListCommand(Command):
    def init_parser(self):
        usage = "schema list [options]" \
                "\n\n" \
                "Note: * denotes that the alter is applied on the database."
        parser = OptionParser(usage=usage)

        parser.add_option('-l', '--list',
                          action='store_true', dest='list', default=True,
                          help="List the [top N] contents of current alter-chain")
        parser.add_option('-L', '--list-from-bottom',
                          action='store_true', dest='listReverse', default=False,
                          help="List the [bottom N] contents of current alter-chain")

        self.parser = parser

    def run(self):
        """
        List the current build chain in the console
        """
        # TODO: add a verbose mode, which shows alters as having been run or not

        (options, args) = self.parser.parse_args()

        list_normal  = options.list
        list_reverse = options.listReverse

        list_tail = ChainUtil.build_chain()

        self.__set_is_applied_flag(list_tail)

        if list_tail is None:
            sys.stdout.write("No alters found\n")
        else:
            normal_str = []
            temp_node = list_tail
            while temp_node is not None:
                normal_str.append(temp_node.__str__(False))
                temp_node = temp_node.backref
            if list_reverse:
                normal_str.reverse()
                print("\n".join(normal_str))
            elif list_normal:
                print("\n".join(normal_str))

    def __set_is_applied_flag(self, chain):
        """
        Sets a flag for each node in the chain whether it has been applied to the
        database or not.
        """
        applied_alters = self.db.get_applied_alters()
        tail = chain
        while tail is not None:
            if tail.id in applied_alters:
                tail.is_applied = True
            else:
                tail.is_applied = False
            tail = tail.backref
