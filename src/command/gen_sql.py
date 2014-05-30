# stdlib imports
from optparse import OptionParser
import os
import sys

# local imports
from command import Command
from constants import Constants
from util import ChainUtil

class GenSqlCommand(Command):
    """
    This command is mainly intended for DBAs as a way to use the tool to
    generate SQL for various alters that they need to run. This command
    will take care of generating statements for the transaction free-time
    table as well as ensuring that alters for revisions are inserted into
    the revision database's history table.
    """
    def init_parser(self):
        usage = "schema gen-sql [options] ref [ref [...]]"
        parser = OptionParser(usage=usage)
        parser.add_option('-R', '--no-revision',
                          action='store_false', dest='gen_revision', default=True,
                          help='Do not print out the revision-history alter statements')
        parser.add_option('-S', '--no-sql',
                          action='store_false', dest='gen_sql', default=True,
                          help='Do not generate SQL for the actual alters, just revision inserts')
        parser.add_option('-d', '--down',
                          action='store_true', dest='down_alter', default=False,
                          help='Generate SQL for down-alter instead of up (default)')
        self.parser = parser

    def run(self):
        (options, args) = self.parser.parse_args()

        # validate has refs
        if args is None or len(args) == 0:
            sys.stderr.write("Error: Must provide one or more revision numbers\n\n")
            self.parser.print_help()
            sys.exit(1)

        refs = args
        nodes = ChainUtil.build_chain()
        ref_nodes = []

        # validate valid refs
        for ref in refs:
            node = self._find_ref(ref, nodes)
            if node is False:
                sys.stderr.write("Error: Ref '%s' could not be found" % ref)
                self.parser.print_help()
                sys.exit(1)
            else:
                ref_nodes.append(node)

        # gen SQL for each ref
        sql = self.gen_sql_for_reflist(ref_nodes, options)

        sys.stdout.write(sql)

    def _find_ref(self, ref, nodes):
        """
        Given a revision (from the command line), check to see if it exists within
        the set of nodes (working backwards). If it does, return the node, else false.
        """
        tail = nodes
        while tail is not None:
            if tail.id == ref:
                return tail
            tail = tail.backref

        return False

    def gen_sql_for_reflist(self, ref_nodes, options):
        """
        Given a set of refs, generate the SQL for
        """
        sql = ''

        for node in ref_nodes:
            sql += self.gen_sql_for_ref(node, options)

        return sql

    def gen_sql_for_ref(self, node, options):
        """
        Gen sql given a node(ref) and the command-line-options,
        """
        sql = ''
        if options.gen_sql:
            try:
                sql_file = None
                if options.down_alter:
                    sql_file = open(os.path.join(Constants.ALTER_DIR, node.down_filename()))
                else:
                    sql_file = open(os.path.join(Constants.ALTER_DIR, node.filename))
                sql = sql_file.read()
                sql += "\n\n"
            except OSError, ex:
                sys.stderr.write("Error opening file '%s'.\n\t=>%s\n" % (os.path.join(Constants.ALTER_DIR, node.filename), ex))
                if 'sql_file' in locals():
                    sql_file.close()
                sys.exit(1)

        if options.gen_revision:
            if options.down_alter:
                sql += "delete from `%s`.`%s` where alter_hash = '%s';\n" % (
                           self.config['revision_db_name'],
                           self.config['history_table_name'],
                           node.id
                       )
            else:
                sql += "insert into `%s`.`%s` (alter_hash, ran_on)" \
                       " values ('%s', NOW());\n" % (
                           self.config['revision_db_name'],
                           self.config['history_table_name'],
                           node.id
                       )

        return sql
