# stdlib imports
from optparse import OptionParser
import os
import re
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

    # TODO@jmurray - is the comment about transaction free-time still relevant?
    """
    def init_parser(self):
        usage = ("schema gen-sql [options] [ref [ref [...]]]\n"
                 "       If no refs are specified, all refs will be used.")
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
        parser.add_option('-q', '--include-rev-query',
                          action='store_true', dest='include_rev_query', default=False,
                          help='Include the revision query in the generated SQL')
        parser.add_option('-w', '--write-to-file',
                          action='store_true', dest='write_to_file', default=False,
                          help=('Do not print to stdout.  Instead, write SQL to file in '
                                '\'static_alter_dir\' directory from config.json.  Implies '
                                '-q/--include-rev-query'))

        self.parser = parser

    def _setup_static_alter_dir(self):
        if self.config.get('static_alter_dir') is None:
            return
        if not os.path.exists(self.config['static_alter_dir']):
            os.makedirs(self.config['static_alter_dir'])

    def run(self):
        (options, args) = self.parser.parse_args()

        # validate static_alter_dir set if flag used
        if options.write_to_file:
            options.include_rev_query = True
            if self.config.get('static_alter_dir') is None:
                raise Exception('static_alter_dir must be set in config.json to'
                                '\nuse -w/--write-to-file flag')
            self._setup_static_alter_dir()

        refs = args
        nodes = ChainUtil.build_chain()
        ref_nodes = []

        if len(refs) == 0:
            # entire chain
            refs = self._get_node_ids(nodes)

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
        if options.write_to_file:
            # gen SQL for each ref, and save to individual files.
            for node in ref_nodes:
                sql = self.gen_sql_for_reflist([node], options)
                if options.down_alter:
                    filename = node.down_filename()
                else:
                    filename = node.filename
                fobj = open(os.path.join(self.config['static_alter_dir'], filename), 'w')
                fobj.write(sql)
                fobj.close()
                print os.path.join(self.config['static_alter_dir'], filename)
        else:
            # gen SQL for refs in one call
            sql = self.gen_sql_for_reflist(ref_nodes, options)
            sys.stdout.write(sql)

    def _get_node_ids(self, nodes):
        result = []
        tail = nodes
        while tail is not None:
            result.append(tail.id)
            tail = tail.backref
        return result

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

        # If only one alter is being processed, there is no reason to add newlines.
        add_newlines = len(ref_nodes) > 1
        for node in ref_nodes:
            sql += self._gen_sql_for_ref(node, options, add_newlines)

        sql = sql.rstrip() + "\n"
        return sql

    def _gen_sql_for_ref(self, node, options, add_newlines):
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
                if add_newlines:
                    sql += "\n\n"

            except OSError, ex:
                sys.stderr.write("Error opening file '%s'.\n\t=>%s\n" % (os.path.join(Constants.ALTER_DIR, node.filename), ex))
                if 'sql_file' in locals():
                    sql_file.close()
                sys.exit(1)

        if options.include_rev_query or options.gen_revision:
            if options.down_alter:
                rev_query = self.db.get_remove_commit_query(node.id)
            else:
                rev_query = self.db.get_append_commit_query(node.id)

            if options.include_rev_query:
                def replace_fn(matchobj):
                    result = ('-- rev query:\n%s\n-- end rev query\n' % rev_query.encode('utf-8'))
                    return matchobj.group(0) + result
                sql = re.sub("-- ref: %s\n" % node.id, replace_fn, sql)
            else:
                sql += rev_query
        return sql
