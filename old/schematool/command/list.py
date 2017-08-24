# stdlib imports
from optparse import OptionParser
import sys

# local imports
from command import Command
from util import ChainUtil

class ListCommand(Command):
    def init_parser(self):
        usage = "schema list [options]" \
                "\n\n" \
                "Note: * denotes that the alter is applied on the database."
        parser = OptionParser(usage=usage)

        parser.add_option('-r', '--reverse',
                          action='store_true', dest='listReverse', default=False,
                          help="List the contents of current alter chain in reverse order")

        self.parser = parser

    def run(self):
        """
        Print the current build chain in the console.

        Return the list of node IDs, which is used for testing.
        """
        # TODO: add a verbose mode, which shows alters as having been run or not

        (options, _) = self.parser.parse_args()

        list_reverse = options.listReverse

        list_tail = ChainUtil.build_chain()

        self.__set_is_applied_flag(list_tail)

        result = []

        if list_tail is None:
            sys.stdout.write("No alters found\n")
        else:
            normal_str = []
            temp_node = list_tail
            while temp_node is not None:
                result.append(temp_node.id)
                normal_str.append(temp_node.__str__(False))
                temp_node = temp_node.backref
            if not list_reverse:
                normal_str.reverse()
                result.reverse()
            sys.stdout.write("\n".join(normal_str) + "\n")

        return result

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
