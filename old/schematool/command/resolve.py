# stdlib imports
from itertools import islice
from optparse import OptionParser
import os
import re
import subprocess
from subprocess import PIPE
import sys

# local imports
from check import CheckCommand
from command import Command
from constants import Constants
from errors import ArgsError, MissingRefError
from gen_ref import GenRefCommand
from util import ChainUtil, MetaDataUtil

class ResolveCommand(Command):
    def __init__(self, context):
        Command.__init__(self, context)
        self.nodes = None
        self.file = None
        self.ref = None
        self.type = None

    def init_parser(self):
        usage = "schema resolve [ref|filename]" \
                "\n\n" \
                "Note: This command currently only resolves divergent files. All\n" \
                "      other issues must be resolved by hand"
        parser = OptionParser(usage=usage)
        # parser.add_option('-f', '--force',
        #                   action='store_true', dest='force', default=False,
        #                   help='Ignore warnings and force the resolution')
        self.parser = parser

    def run(self):
        """
        Future Functionality:
            Given a filename or a reference, determine what actually needs to be resolved
            and then attempt to automatically resolve the issue. The current items that
            will be attempted to address include (in order of how they would be addressed):
                - filename standards     => attempt to rename file to meet standards
                - divergent chains       => append to end of alter chain and rename file
                - abandoned alters       => append to end of alter chain and rename file
                - missing up/down        => create the missing pair

        Current Functionality:
            Given a filename, resolve a conflict that is happening by moving the file
            to the end of the build chain. First however, verify that this alter hasn't
            been run in the DB. If so, require the force option to continue.

            If the alter is at the end of the db history then we can also warn and, if
            given the force option, can undo the commit before resolving (should issue
            message about what has happened).
        """
        (_, args) = self.parser.parse_args()

        if len(args) == 0:
            raise ArgsError("You must provide a filename or reference", self.parser.format_help())

        # search for file/ref
        self.file = self.ref = args[0]
        if self._file_exists():
            self.type = 'file'
        elif self._ref_exists():
            self.type = 'ref'
        else:
            raise MissingRefError("Filename or reference not found for '%s'" % self.file)

        # We can now assume that self.ref and self.file are set properly

        # TODO: implement ability to determine issue and resolve (if possible) automatically
        # determine what the issue is:
        # check = CheckCommand()
        # if not check.check_filename(self.file):
        #     # rename file
        #     pass

        sys.stdout.write("Resolving\n")
        self._relocate_sub_chain()

        sys.stdout.write("\nRe-Checking...\n")
        sys.argv = [sys.argv[0]]
        CheckCommand(self.context).run()

    def _file_exists(self):
        """
        Check that the file exists. Also try to check the absolute path. If the
        file is found within the absolute path, then update the file path
        """
        file_found = True
        if not os.path.exists(self.file):
            if os.path.exists(os.path.join(Constants.ALTER_DIR, self.file)):
                self.file = os.path.join(Constants.ALTER_DIR, self.file)
            else:
                file_found = False

        # populate ref if file found
        if file_found:
            try:
                my_file = open(self.file)
                head = list(islice(my_file, 3))
            except OSError, ex:
                if 'my_file' in locals():
                    my_file.close()
                sys.stderr.write("Error reading file '%s'\n\t=>%s\n" % (self.file, ex.message))

            if not MetaDataUtil.parse_direction(head) == 'up':
                sys.stderr.write("File can only be an up-alter: '%s'" % self.file)

            meta_data = MetaDataUtil.parse_meta(head)
            if 'ref' in meta_data:
                self.ref = meta_data['ref']

        return file_found

    def _ref_exists(self):
        """
        Check that the references (self.ref) exists within the build-chain. And, if so,
        set the filename to the appropariate name given the reference
        """
        self._collect_soft_chain()

        found_ref = False
        for node in self.nodes:
            if node.id == self.ref:
                self.file = os.path.join(Constants.ALTER_DIR, node.filename)
                found_ref = True
                break

        return found_ref

    def _file_in_conflict(self):
        """
        Check that the file (self.file) is actually in conflict before resolving.
        If the force option is given, then this can/will be ignored.
        """
        # TODO: implement. probably need to factor out soft-chain validation
        self._collect_soft_chain()
        # TODO - raise an error from errors.py here.
        sys.exit(1)

    def _collect_soft_chain(self):
        """
        Build the soft-chain if it is not already defined and return
        the chain
        """
        if not self.nodes:
            files = ChainUtil.get_alter_files()
            self.nodes = ChainUtil.build_soft_chain(files)

        return self.nodes

    def _relocate_sub_chain(self):
        """
        Given a ref and filename to start from, we need to relocate a
        sub-chain (that is in conflict to the end of the current alter chain).
        """
        self._collect_soft_chain()

        # get each file in sub-chain
        head = [n for n in self.nodes if n.id == self.ref]
        if len(head) > 1:
            raise Exception("Error resolving (1)")
        elif len(head) == 0:
            raise Exception("Error resolving (2)")
        else:
            head = head[0]

        sub_chain = []
        while head is not None:
            sub_chain.append(head)
            head = [n for n in self.nodes if n.backref == head.id]
            if len(head) > 1:
                raise Exception("Error resolving (3)")
            elif len(head) == 0:
                head = None
            else:
                head = head[0]

        sub_chain.reverse()

        # find tail of correct chain
        # (as long as it's not the tail of the sub-chain, we should be good)
        tails = []
        for node in self.nodes:
            children = [n for n in self.nodes if n.backref == node.id]
            if len(children) == 0:
                tails.append(node)

        tails = [t for t in tails if t not in sub_chain]
        if len(tails) == 0:
            raise Exception("Error resolving (4)")
        tail = tails[0] # just have to pick one

        # for each file in the sub-chain relocate head of the chain behind
        # correct chain's tail (making it the new tail)
        i = 0
        while len(sub_chain) > 0:
            node = sub_chain.pop()

            # gen new ref
            new_ref = (GenRefCommand(self.context)).gen_ref(i)

            # generate new file-names
            new_up_filename = self._rename_file(filename=node.filename, ref=new_ref)
            new_down_filename = self._rename_file(filename=node.down_filename(), ref=new_ref)

            # move files and edit meta-data (new [back]ref)
            self._relocate_files(
                old_filename=node.filename,
                new_filename=new_up_filename,
                new_ref=new_ref,
                new_backref=tail.id,
                direction='up')
            self._relocate_files(
                old_filename=node.down_filename(),
                new_filename=new_down_filename,
                new_ref=new_ref,
                new_backref=tail.id,
                direction='down')

            # update tail = node
            node.id = new_ref
            node.backref = tail.id
            node.filename = new_up_filename

            tail = node
            i += 1

    def _rename_file(self, filename, ref):
        """
        Given a filename and a ref, rename the filename to the new use the new ref
        and return the new filename.
        """
        r = re.compile('^(\d{12})')
        return r.sub(ref, filename)

    def _relocate_files(self, old_filename, new_filename, new_ref, new_backref, direction):
        """
        Move the file on disk. Not really a big task, but it might be nice in the
        future to go ahead and do a git mv command for the user.
        """
        is_backref_line = re.compile('--\s*backref\s*:\s*(\d+)')
        is_ref_line     = re.compile('--\s*ref\s*:\s*(\d+)')

        found_ref     = False
        found_backref = False

        old_filename_with_dir = os.path.join(Constants.ALTER_DIR, old_filename)
        new_filename_with_dir = os.path.join(Constants.ALTER_DIR, new_filename)

        # create the new file
        try:
            new_file = open(new_filename_with_dir, 'w')
            old_file = open(old_filename_with_dir, 'r')
            lines = old_file.readlines()
            for line in lines:
                if not found_ref and is_ref_line.match(line) is not None:
                    new_file.write('-- ref: %s\n' % new_ref)
                    found_ref = True
                elif not found_backref and is_backref_line.match(line) is not None:
                    new_file.write('-- backref: %s\n' % new_backref)
                    found_backref = True
                else:
                    new_file.write(line)

            new_file.close()
            old_file.close()
        except OSError, ex:
            sys.stderr.write("Error renaming file '%s'\n\t=>%s\n" % (old_filename_with_dir, ex.message))
            if 'new_file' in locals():
                new_file.close()
            if 'old_file' in locals():
                old_file.close()

        # delete the old file
        try:
            os.remove(old_filename_with_dir)
        except OSError, ex:
            sys.stderr.write("Could not delete file '%s'\n\t=>%s\n" % (old_filename_with_dir, ex.message))

        # create the new static file
        if self.config.get('static_alter_dir'):
            old_static_filename = os.path.join(self.config['static_alter_dir'], old_filename)
            new_static_filename = os.path.join(self.config['static_alter_dir'], new_filename)

            content = open(new_filename_with_dir).read()
            if direction == 'up':
                rev_query = self.db.get_append_commit_query(new_ref)
            else:
                assert direction == 'down'
                rev_query = self.db.get_remove_commit_query(new_ref)
            content += '\n\n-- start rev query\n%s;\n-- end rev query\n' % rev_query.encode('utf-8')
            f = open(new_static_filename, 'w')
            f.write(content)
            f.close()

            # delete the old static file, and add the new static file.
            static_file_commands = [
                ['git', 'rm', '--ignore-unmatch', old_static_filename],
                ['git', 'add', new_static_filename],
            ]
        else:
            static_file_commands = []

        # perform Git updates (add and rm -> rename in essence)
        commands = [
            ['git', 'rm', '%s' % old_filename_with_dir],
            ['git', 'add', '%s' % new_filename_with_dir],
        ] + static_file_commands

        try:
            for cmd in commands:
                proc = subprocess.Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
                _, stderr = proc.communicate()

                if not proc.returncode == 0 and stderr is not None:
                    sys.stderr.write("Error")
                    sys.stderr.write("\n----------------------\n")
                    sys.stderr.write(proc.stderr)
                    sys.stderr.write("\n----------------------\n")
                    sys.stderr.write("\n")
        except Exception, ex:
            sys.stderr.write("Error performing git operations\n\t=>%s\n" % ex.message)
