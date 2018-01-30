# stdlib imports
from optparse import OptionParser
import sys
from time import time

# local imports
from command import Command


class GenRefCommand(Command):
    def init_parser(self):
        useage = "schema gen-ref"
        parser = OptionParser(usage=useage)
        self.parser = parser

    def run(self):
        """
        Just generate a timestamp and return it to the console. We'll consider this
        a "hash" or "ref" for our purposes
        """
        self.parser.parse_args()

        sys.stdout.write("ref: %s\n\n" % self.gen_ref())

    def gen_ref(self, inc=0):
        int_ref = round(time() * 10) + (inc / 10.0)
        return str(int_ref).replace('.', '')
