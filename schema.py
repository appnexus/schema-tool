#!/usr/bin/env python2.7

# File: schema
# Author: John Murray <jmurray@appnexus.com>
#
# This is a utility file for working with DB alters in the root
# folder which should include alters for (at time of writing):
#   - api
#   - audit
#   - bidder
#   - common
#   - inventory_quality
#
# For more information on how to use the script, call with the '-h'
# option.
#
# TODO: The entire file could use a little refactoring from my poor Python skills
# TODO: All these top-level functions should probably be in classes and utilities


import os
import re
import subprocess
import sys

(v_major, v_minor, _, _, _) = sys.version_info
if v_major == 2 and v_minor < 6:
    import simplejson as json
else:
    import json

from itertools import islice
from optparse import OptionParser
from subprocess import PIPE
from time import time
from traceback import print_exc

from db import MySQLDb, PostgresDb

MAINTAINER = "John Murray <jmurray@appnexus.com>"

#ALTER_DIR = os.path.dirname(os.path.abspath(__file__)) + '/../'
ALTER_DIR = os.path.abspath(os.path.curdir) + '/'

COMMANDS = [
    {'command': 'new',      'handler': 'NewCommand'},
    {'command': 'check',    'handler': 'CheckCommand'},
    {'command': 'list',     'handler': 'ListCommand'},
    {'command': 'up',       'handler': 'UpCommand'},
    {'command': 'down',     'handler': 'DownCommand'},
    {'command': 'rebuild',  'handler': 'RebuildCommand'},
    {'command': 'gen-ref',  'handler': 'GenRefCommand'},
    {'command': 'resolve',  'handler': 'ResolveCommand'},
    {'command': 'init',     'handler': 'InitCommand'},
    {'command': 'gen-sql',  'handler': 'GenSqlCommand'}
]

#CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
CONFIG_FILE = os.path.join(ALTER_DIR, 'config.json')

FILENAME_STANDARD = re.compile('^\d{12}-.+-(up|down)\.sql$')


def main(config):
    """
    Determine what command is being called and dispatch it to the appropriate
    handler. If the command is unknown or the '-h' flag has been given, display
    the help file.
    """
    commands = [
        "  new         Create a new alter",
        "  check       Check that all back-refs constitute a valid chain",
        "  list        List the current alter-chain",
        "  up          Bring up to particular revision",
        "  down        Roll back to a particular revision",
        "  rebuild     Run the entire database down and back up (hard refresh)",
        "  gen-ref     Generate new file-ref",
        "  gen-sql     Generate SQL for a given reference, including revision-history alter(s)",
        "  resolve     Resolve a divergent-branch conflict (found by 'check' command)",
        "  init        Initialize new project",
        "  help        Show this help message and exit"
    ]
    usage = "schema command [options]\n\nCommands:\n" + ("\n".join(commands))
    parser = OptionParser(usage=usage)

    if len(sys.argv) == 1 or sys.argv[1] in ['-h', '--help', 'help']:
        if len(sys.argv) < 2:
            sys.stderr.write("Error: No commands or options given, view -h for each\n" +
                             "       command for more information\n\n")
        parser.print_help()
        sys.exit(1)

    # check if the command given is valid and dispatch appropriately
    user_command = sys.argv[1]
    if user_command in [c['command'] for c in COMMANDS]:
        sys.argv = sys.argv[1:]
        handler = [c['handler'] for c in COMMANDS if c['command'] == user_command][0]
        try:
            globals()[handler](config).run()
        except SystemExit:
            sys.exit(1)
        except EnvironmentError, er:
            sys.stderr.write(
                "An exception has occurred... Sorry. You should gripe to %s about this\n\n" % (
                    MAINTAINER))
            sys.stderr.write("Error: %s, %s\n\n" % (er.errno, er.strerror))
            sys.exit(1)
        except Exception, ex:
            sys.stderr.write(
                "An exception has occurred... Sorry. You should gripe to %s about this\n\n" % (
                    MAINTAINER))
            sys.stderr.write("Error: %s\n\n" % ex)
            print_exc()
            sys.exit(1)
    else:
        sys.stderr.write("No command '%s' defined\n\n" % sys.argv[1])
        parser.print_help()


def build_chain():
    """
    Walk the schemas directory and build the chain of alterations that should be run. Also
    return a list of "out-of-chain" items that don't quite fit.

    Returns tail of list representing current files
    :rtype : SimpleNode
    """
    files     = get_alter_files()
    nodes     = build_soft_chain(files)
    list_tail = build_and_validate_linked_list(nodes)

    # some debug statements
    # print("%r\n" % nodes)
    # print("%s\n" % list_tail)

    return list_tail


def get_alter_files():
    files = os.walk(ALTER_DIR).next()[2]
    return [f for f in files if FILENAME_STANDARD.search(f)]


def build_soft_chain(files):
    """
    Build a list of nodes "soft" linked. This means that each has an id
    (an integer value) and possibly a backref which is also an integer.
    Not a truly "linked" list

    Returns an array of SimpleNodes
    :rtype : list
    """
    nodes = []

    for f in files:
        if not FILENAME_STANDARD.search(f):
            continue

        try:
            my_file = open(os.path.join(ALTER_DIR, f))
            head = list(islice(my_file, 3))
        except OSError, ex:
            sys.stderr.write("Error opening file '%s'.\n\t=>%s\n" % (os.path.join(ALTER_DIR, f), ex.message))
            sys.exit(1)

        if not parse_direction(head) == 'up':
            continue

        refs = parse_meta(head)

        if not 'ref' in refs:
            continue

        node = SimpleNode(filename=f, id=refs['ref'])
        if 'backref' in refs:
            node.backref = refs['backref']

        nodes.append(node)

    return nodes


def build_and_validate_linked_list(nodes):
    """
    Build a linked list and validate it's correctness given an array of
    SimpleNodes contain soft/weak references to each other

    Returns tail of list (since it's processed backwards)
    :rtype : SimpleNode
    """
    # check if we're working with no nodes, return None if so
    # don't error/exit because and empty list is not necessarily invalid
    if len(nodes) == 0:
      return None

    heads = []
    backrefs = {}
    for node in nodes:
        if node.backref is not None:
            # Check for duplicate refs
            backnodes = [n for n in nodes if n.id == node.backref]
            if len(backnodes) > 1:
                for b in backnodes:
                    sys.stderr.write("Duplicate refs found in %s\n" % b.filename)
                sys.exit(1)
            elif len(backnodes) == 1:
                node.backref = backnodes[0]
            else:
                sys.stderr.write("Backref points to non-existent alter: %s\n" % node.filename)
                sys.exit(1)

            # catalog backrefs (for divergence checking)
            if node.backref.id not in backrefs:
                backrefs[node.backref.id] = []
            backrefs[node.backref.id].append(node)
        else:
            heads.append(node)

    # check backref catalog for duplicates
    for (backref_id, _nodes) in backrefs.iteritems():
        if len(_nodes) > 1:
            sys.stderr.write("Divergent Branch:"
                             "\nThis means that we have found alters that share a common parent. To fix"
                             "\nthis you can run the 'resolve' command. When merging changes from your"
                             "\nfeature-branch, ensure that you resolve your files that are in conflict"
                             "\n(not existing files that were previously in a good state)."
                             "\n\n")
            for node in _nodes:
                sys.stderr.write("\tDuplicate backref found (divergent branch): %s\n" % node.filename)
            sys.stderr.write("\n")
            sys.exit(1)

    # check head(s)
    if len(heads) > 1:
        sys.stderr.write("More than one head found:\n")
        for head in heads:
            sys.stderr.write("  %s\n" % head.filename)
        sys.exit(1)
    elif len(heads) == 0:
        sys.stderr.write("No head found\n")
        sys.exit(1)

    # check tail(s)
    tails = []
    for node in nodes:
        if node.backref is None:
            continue
        children = [n for n in nodes if n.backref == node]
        if len(children) == 0:
            tails.append(node)

    if len(tails) > 1:
        for tail in tails:
            sys.stderr.write("Duplicate backref found in %s\n" % tail.filename)
        sys.exit(1)
    elif len(tails) == 0 and (not len(nodes) == 1):
        sys.stderr.write("something strange is happening... no last alter found (circular references!!)\n")
        sys.exit(1)

    if len(nodes) == 1:
        return heads[0]
    else:
        return tails[0]


def parse_direction(head):
    """
    Given the entire head meta-data (an array of strings) parse out
    the direction of the alter (up/down) and return that value.

    Returns a string 'up' or 'down' or None if nothing can be parsed
    from the given input
    """
    head = [h.strip() for h in head]
    direction = None
    for line in head:
        direction = _parse_line_for_direction(line) or direction

    return direction


def _parse_line_for_direction(line):
    """
    Given a single line, see if we can parse out the alter-direction (up/down
    sql) and return the direction 'up' or 'down'. If nothing can be parsed out
    of the line, then return None
    """
    if line is None:
        return None

    if not line[0:2] == '--':
        return None
    regex = re.compile('--\s*')
    line = regex.sub('', line)

    up_regex   = re.compile('direction\s*:\s*(up)')
    down_regex = re.compile('direction\s*:\s*(down)')

    up   = up_regex.match(line)
    down = down_regex.match(line)

    if up is not None:
        return up.groups()[0]
    elif down is not None:
        return down.groups()[0]
    else:
        return None


def parse_meta(head):
    """
    Given the top two lines of the file, parse the meta-data and what have
    you. Really just the refs (this-ref and back-ref)

    Return a dict of this-ref and back-ref as:
    {"ref": int, "backref": int}

    Note: may not have a backref if first element, but should always have a ref
    """
    head = [h.rstrip() for h in head]
    refs = {}
    for line in head:
        (ref, ref_type) = parse_ref(line)
        if not ref_type == 'none':
            refs[ref_type] = ref
    return refs


def parse_ref(line):
    """
    Parse out the ref, or backref, of the meta-data that is stored at the top
    of each SQL file.
    """
    if not line[0:2] == '--':
        return None, 'none'
    regex = re.compile('--\s*')
    line = regex.sub('', line)

    ref_match     = re.compile('ref\s*:\s*(\d+)')
    backref_match = re.compile('backref\s*:\s*(\d+)')

    rm  = ref_match.match(line)
    brm = backref_match.match(line)

    if rm is not None:
        rid = rm.groups()[0]
        return rid, 'ref'
    elif brm is not None:
        br_id = brm.groups()[0]
        return br_id, 'backref'
    else:
        return None, 'none'


def load_config():
    """
    Read the config file and return the values
    """
    try:
        config_file = open(CONFIG_FILE, 'r')
        try:
            config = json.load(config_file)
        except ValueError, ex:
            sys.stderr.write("Could not parse config file: %s\n" % ex.message)
            sys.exit(1)
    except IOError, ex:
        sys.stderr.write("Error reading config: %s\n" % ex.strerror)
        sys.stderr.write("Tried reading: %s\n" % CONFIG_FILE)
        sys.exit(1)
    return config

def set_is_applied_flag(chain):
    """
    Sets a flag for each node in the chain whether it has been applied to the
    database or not.
    """
    applied_alters = _DB.get_applied_alters()
    tail = chain
    while tail is not None:
        if tail.id in applied_alters:
            tail.is_applied = True
        else:
            tail.is_applied = False
        tail = tail.backref

# SUPPORT CLASSES
class SimpleNode:
    """
    Represents a simple node within the alter-chain. Just makes things
    a little easier and what not.
    """
    def __init__(self, id, filename):
        self.id = id
        self.backref = None
        self.filename = filename

        self.re_num       = re.compile('^\d{12}-')
        self.re_direction = re.compile('-(up|down).sql$')

        self.is_applied = None

    def __str__(self, recursive=True):
        out = ''
        if self.backref is not None:
            out += '-> '
        else:
            out += '   '
        filename = self.re_num.sub('', self.filename)
        filename = self.re_direction.sub('', filename)
        if self.is_applied:
            out += '*'
        else:
            out += ' '
        out += ("[%s] %s" % (str(self.id), filename))

        if recursive:
            if self.backref is not None:
                out = str(self.backref) + "\n" + out

        return out

    def __repr__(self):
        return self.__str__(recursive=False)

    def down_filename(self):
        return self.filename.replace('up.sql', 'down.sql')

    def abs_filename(self, direction='up'):
        if direction == 'up':
            return os.path.join(ALTER_DIR, self.filename)
        elif direction == 'down':
            return os.path.join(ALTER_DIR, self.down_filename())
        else:
            sys.stderr.write("%s is not a valid alter-direction" % direction)
            return None


# COMMAND CLASSES
class Command(object):
    """
    The general command object. Does fun stuff...
    """
    def __init__(self, config):
        self.config = config
        self.init_parser()

    def init_parser(self):
        """
        Initialize all option-parsing stuff and store into self.parser
        """
        pass


class NewCommand(Command):
    def init_parser(self):
        usage = "schema new [options]"
        parser = OptionParser(usage=usage)
        parser.add_option('-f', '--file',
                          dest="filename", action="store",
                          help="The name of the new file")

        self.parser = parser

    def run(self):
        """
        Run the "new" command as if it were it's own executable. This means
        processing any options and performing the task of creating a new
        alter file.

        Note: This command assumes a starting point that has been created
        manually (and a working db-directory)
        """
        (options, args) = self.parser.parse_args()

        timestamp = str(round(time() * 10)).replace('.', '')
        filename = timestamp + '-' + (options.filename or '_').replace('.sql', '')

        alter_list_tail = build_chain()

        if alter_list_tail is not None:
            sys.stdout.write("Parent file:  %s\n" % alter_list_tail.filename)

        up_filename = filename + '-up.sql'
        try:
            alter_file = open(os.path.join(ALTER_DIR, up_filename), 'w')
            alter_file.write("-- direction: up\n")
            if alter_list_tail is not None:
                alter_file.write("-- backref: %s\n" % alter_list_tail.id)
            alter_file.write("-- ref: %s\n" % timestamp)
            alter_file.write("\n\n\n")
        except OSError, ex:
            sys.stderr.write("Error writing file '%s'\n\t=>%s\n" % (os.path.join(ALTER_DIR, up_filename), ex.message))
            sys.exit(1)
        sys.stdout.write("Created file: %s\n" % up_filename)

        down_filename = filename + '-down.sql'
        try:
            alter_file = open(os.path.join(ALTER_DIR, down_filename), 'w')
            alter_file.write("-- direction: down\n")
            if alter_list_tail is not None:
                alter_file.write("-- backref: %s\n" % alter_list_tail.id)
            alter_file.write("-- ref: %s\n" % timestamp)
            alter_file.write("\n\n\n")
        except OSError, ex:
            sys.stderr.write("Error writing file '%s'\n\t=>%s\n" % (os.path.join(ALTER_DIR, up_filename), ex.message))
            sys.exit(1)
        sys.stdout.write("Created file: %s\n" % down_filename)


class CheckCommand(Command):
    def init_parser(self):
        usage = "schema check [options]"
        parser = OptionParser(usage=usage)
        parser.add_option('-v', '--verbose',
                          action='store_true', dest='verbose', default=False,
                          help='Enable verbose message output')
        self.parser = parser

    def run(self, inline=False):
        """
        Check that the alter-chain is valid

        """
        # TODO  Check that the alter-chain is in line with the DB (but not necessarily up to date)
        # TODO  Make the verbose flag do something based on previous additions
        # TODO  Add flags to only perform certain checks (as described in the other todos)

        if not inline:
            (options, args) = self.parser.parse_args()

        self.files = get_alter_files()

        # implicitly check validity of chain (integrety check)
        chain = build_chain()

        # all other checks
        self.check_abandoned_alters(chain)
        self.check_missing_pair()
        self.check_filenames()

        if not inline:
            print("Everything looks good!\n")

    def check_abandoned_alters(self, chain):
        """
        Check for files that do not exist within the current alter-chain.
        """
        tail = chain
        chain_files = []
        while tail is not None:
            chain_files.append(tail.filename)
            tail = tail.backref

        up_alter = re.compile('-up.sql')
        for file in self.files:
            if up_alter.search(file) is not None:
                if file not in chain_files:
                    sys.stderr.write("File not found within build-chain '%s'\n" % file)
                    sys.exit(1)

    def check_missing_pair(self):
        """
        Check for any alters that have an up, but not a down and vice-versa
        """
        up_alter = re.compile('-up.sql')
        down_alter = re.compile('-down.sql')
        for file in self.files:
            if up_alter.search(file) is not None:
                down_file = up_alter.sub('-down.sql', file)
                if not os.path.exists(os.path.join(ALTER_DIR, down_file)):
                    sys.stderr.write("No down-file found for '%s', expected '%s'\n" % (
                        file, down_file))
                    sys.exit(1)
            elif down_alter.search(file) is not None:
                up_file = down_alter.sub('-up.sql', file)
                if not os.path.exists(os.path.join(ALTER_DIR, up_file)):
                    sys.stderr.write("No up-file found for '%s', expected '%s'\n" % (
                        file, up_file))
                    sys.exit(1)

    def check_filenames(self):
        """
        Raise an error to the user and exit if a file fails to meet
        our standards.
        """
        for file in self.files:
            if not self.check_filename(file):
                sys.stderr.write("File does not match standard format: '%s'\n" % file)
                sys.stderr.write("Perhaps you should use the 'new' command to create alter-files\n")
                sys.exit(1)

    def check_filename(self, filename):
        """
        Check that the givenfilename meets our standards.
        """
        return FILENAME_STANDARD.search(filename) is not None


class ResolveCommand(Command):
    def __init__(self, config):
        Command.__init__(self, config)
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
                - divergent chains       => append to end of alter-chain and rename file
                - abandoned alters       => append to end of alter-chain and rename file
                - missing up/down        => create the missing pair

        Current Functionality:
            Given a filename, resolve a conflict that is happening by moving the file
            to the end of the build chain. First however, verify that this alter hasn't
            been run in the DB. If so, require the force option to continue.

            If the alter is at the end of the db history then we can also warn and, if
            given the force option, can undo the commit before resolving (should issue
            message about what has happened).
        """
        (options, args) = self.parser.parse_args()

        if len(args) == 0:
            sys.stderr.write("You must provide a filename or reference\n")
            self.parser.print_help()
            sys.exit(1)

        # search for file/ref
        self.file = self.ref = args[0]
        if self._file_exists():
            self.type = 'file'
        elif self._ref_exists():
            self.type = 'ref'
        else:
            sys.stderr.write("Filename or reference not found for '%s'\n" % self.file)
            sys.exit(1)

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
        CheckCommand(self.config).run()

    def _file_exists(self):
        """
        Check that the file exists. Also try to check the absolute path. If the
        file is found within the absolute path, then update the file path
        """
        file_found = True
        if not os.path.exists(self.file):
            if os.path.exists(os.path.join(ALTER_DIR, self.file)):
                self.file = os.path.join(ALTER_DIR, self.file)
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

            if not parse_direction(head) == 'up':
                sys.stderr.write("File can only be an up-alter: '%s'" % self.file)

            refs = parse_meta(head)
            if 'ref' in refs:
                self.ref = refs['ref']

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
                self.file = os.path.join(ALTER_DIR, node.filename)
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
        sys.exit(1)

    def _collect_soft_chain(self):
        """
        Build the soft-chain if it is not already defined and return
        the chain
        """
        if not self.nodes:
            files = get_alter_files()
            self.nodes = build_soft_chain(files)

        return self.nodes

    def _relocate_sub_chain(self):
        """
        Given a ref and filename to start from, we need to relocate a
        sub-chain (that is in conflict to the end of the current alter-chain.
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
            new_ref = (GenRefCommand(self.config)).gen_ref(i)

            # generate new file-names
            new_up_filename = self._rename_file(filename=node.filename, ref=new_ref)
            new_down_filename = self._rename_file(filename=node.down_filename(), ref=new_ref)

            # move files and edit meta-data (new [back]ref)
            self._relocate_files(
                old_filename=node.filename,
                new_filename=new_up_filename,
                new_ref=new_ref,
                new_backref=tail.id)
            self._relocate_files(
                old_filename=node.down_filename(),
                new_filename=new_down_filename,
                new_ref=new_ref,
                new_backref=tail.id)

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

    def _relocate_files(self, old_filename, new_filename, new_ref, new_backref):
        """
        Move the file on disk. Not really a big task, but it might be nice in the
        future to go ahead and do a git mv command for the user.
        """
        is_backref_line = re.compile('--\s*backref\s*:\s*(\d+)')
        is_ref_line     = re.compile('--\s*ref\s*:\s*(\d+)')

        found_ref     = False
        found_backref = False

        old_filename = os.path.join(ALTER_DIR, old_filename)
        new_filename = os.path.join(ALTER_DIR, new_filename)

        # create the new file
        try:
            new_file = open(new_filename, 'w')
            old_file = open(old_filename, 'r')
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
            sys.stderr.write("Error renaming file '%s'\n\t=>%s\n" % (old_filename, ex.message))
            if 'new_file' in locals():
                new_file.close()
            if 'old_file' in locals():
                old_file.close()

        # delete the old file
        try:
            os.remove(old_filename)
        except OSError, ex:
            sys.stderr.write("Could not delete file '%s'\n\t=>%s\n" % (old_filename, ex.message))

        # perform Git updates (add and rm -> rename in essence)
        try:
            command = ['git', 'rm', '%s' % old_filename]
            proc = subprocess.Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            proc.wait()

            if not proc.returncode == 0 and proc.stderr is not None:
                sys.stderr.write("Error")
                sys.stderr.write("\n----------------------\n")
                sys.stderr.write(proc.stderr)
                sys.stderr.write("\n----------------------\n")
                sys.stderr.write("\n")

            command = ['git', 'add', '%s' % new_filename]
            proc = subprocess.Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            proc.wait()

            if not proc.returncode == 0 and proc.stderr is not None:
                sys.stderr.write("Error")
                sys.stderr.write("\n----------------------\n")
                sys.stderr.write(proc.stderr)
                sys.stderr.write("\n----------------------\n")
                sys.stderr.write("\n")
        except Exception, ex:
            sys.stderr.write("Error performing git operations\n\t=>%s\n" % ex.message)


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

        list_tail = build_chain()

        set_is_applied_flag(list_tail)

        if list_tail is None:
            sys.stdout.write("No alters found\n")
        else:
            if list_reverse:
                normal_str = str(list_tail).splitlines()
                normal_str.reverse()
                print("\n".join(normal_str))
            elif list_normal:
                print("%s" % list_tail)


class UpCommand(Command):
    def init_parser(self):
        usage = "schema up [options] [ref]" \
                "\n\n" \
                "Arguments" \
                "\n  ref               Rn all alters up to, and including the ref given"
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

        CheckCommand(self.config).run(inline=True)

        # get history
        history = _DB.get_commit_history()
        history = sorted(history, key=lambda h: h[0])

        # get current alter-chain
        tail = build_chain()
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

        # undo alters that are not in sync with alter chain
        uncommon_history = history[common_history:]
        if len(uncommon_history) > 0:
            # clean up alters from here
            uncommon_history.reverse()
            for (_id, alter_id, datetime) in uncommon_history:
                alters = [a for a in alter_list if a.id == alter_id]
                if len(alters) > 0:
                    sys.stderr.write("Multiple alters found for a single id\n")
                    if not options.force:
                        sys.exit(1)
                alter = alters[0]
                _DB.run_down(alter)

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
            _DB.run_up(alter=alter,
                      force=options.force,
                      verbose=options.verbose)

        sys.stdout.write("Updated\n")


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

        # check validity of options (can't really do this in OptionParser AFAIK)
        if len(args) == 0 and options.N is None:
            sys.stderr.write("Error: must specify either argument or number of down-alters to run\n\n")
            self.parser.print_help()
            sys.exit(1)

        # get current history
        history = _DB.get_commit_history()
        history = sorted(history, key=lambda h: h[0], reverse=True)

        # get current alter-chain
        tail = build_chain()
        alter_list = [tail]
        if None in alter_list:
            alter_list.remove(None)
        while tail is not None and tail.backref is not None:
            tail = tail.backref
            alter_list.append(tail)

        # collect the down-alters that we need to run depending on the command line
        # options and arguments that were given
        down_alters_to_run = []
        max = int(options.N or len(history))
        i = 0
        for (id, alter_id, datetime) in history:
            if i == max:
                break
            if len(args) > 0:
                if args[0] == 'base':
                    if i == (max - 1):
                        break
                elif args[0] == 'all':
                    pass
                else:
                    target_rev = args[0]
                    if target_rev == alter_id:
                        i = (max - 1)

            i += 1
            alters = [a for a in alter_list if a.id == alter_id]
            if len(alters) > 0:
                alter = alters[0]
                down_alters_to_run.append(alter)
            else:
                # error depending on the force and verbose flags (missing alter to run)
                if options.force:
                    sys.stderr.write("Warning: missing alter: %s\n" % alter_id)
                    _DB.remove_commit(ref=alter_id)
                else:
                    sys.stderr.write("error, missing alter: %s\n" % alter_id)
                    sys.exit(1)

        # run all the down-alters that we have collected
        for alter_to_run in down_alters_to_run:
            _DB.run_down(alter=alter_to_run,
                        force=options.force,
                        verbose=options.verbose)

        sys.stdout.write("Downgraded\n")


class RebuildCommand(Command):
    def init_parser(self):
        usage = "schema rebuild [options]"
        parser = OptionParser(usage=usage)
        parser.add_option('-f', '--force',
                          action='store_true', dest='force', default=False,
                          help='Continue running alters even if an error has occurred')
        parser.add_option('-v', '--verbose',
                          action='store_true', dest='verbose', default=False,
                          help='Output verbose error-messages when used with -f option if errors are encountered')
        self.parser = parser

    def run(self):
        (options, args) = self.parser.parse_args()

        sys.stdout.write("Bringing all the way down\n")
        sys.argv = [sys.argv[0]]
        if options.force:
            sys.argv.append('--force')
        if options.verbose:
            sys.argv.append('--verbose')
        sys.argv.append('all')
        DownCommand(self.config).run()

        sys.stdout.write("\nBringing all the way back up\n")
        sys.argv = [sys.argv[0]]
        if options.force:
            sys.argv.append('--force')
        if options.verbose:
            sys.argv.append('--verbose')
        UpCommand(self.config).run()


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
        nodes = build_chain()
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
                    sql_file = open(os.path.join(ALTER_DIR, node.down_filename()))
                else:
                    sql_file = open(os.path.join(ALTER_DIR, node.filename))
                sql = sql_file.read()
                sql += "\n\n"
            except OSError, ex:
                sys.stderr.write("Error opening file '%s'.\n\t=>%s\n" % (os.path.join(ALTER_DIR, node.filename), ex))
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

class InitCommand(Command):
    def init_parser(self):
        usage = "schema init [options]"
        parser = OptionParser(usage=usage)
        parser.add_option('-f', '--force',
                          action='store_true', dest='force', default=False,
                          help='Forcibly init the table (wiping all old data)')
        self.parser = parser

    def run(self):
        """
        Initialize everything if this is the first time that the tool has been run
        """
        (options, args) = self.parser.parse_args()
        _DB.init(force=options.force)

# Start the script
if __name__ == "__main__":
    config = load_config()
    global _DB
    if 'type' in config:
        if config['type'] == 'postgres':
            _DB = PostgresDb.new(config)
        elif config['type'] == 'mysql':
            _DB = MySQLDb.new(config)
        else:
            sys.stderr.write('Invalid database type in config. Only \'postgres\' and \'mysql\' \
            are allowed.')
            sys.exit(1)
    else:
        _DB = MySQLDb.new(config)
    main(config)
