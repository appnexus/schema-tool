from itertools import islice
import os
import sys

from metadata import MetaDataUtil
from node import SimpleNode
from constants import Constants

class ChainUtil(object):
    @classmethod
    def build_chain(cls):
        """
        Walk the schemas directory and build the chain of alterations that should be run. Also
        return a list of "out-of-chain" items that don't quite fit.
    
        Returns tail of list representing current files
        :rtype : SimpleNode
        """
        files     = cls.get_alter_files()
        nodes     = cls.build_soft_chain(files)
        list_tail = cls.__build_and_validate_linked_list(nodes)
    
        # some debug statements
        # print("%r\n" % nodes)
        # print("%s\n" % list_tail)
    
        return list_tail


    @classmethod
    def get_alter_files(cls):
        files = os.walk(Constants.ALTER_DIR).next()[2]
        return [f for f in files if Constants.FILENAME_STANDARD.search(f)]


    @classmethod
    def build_soft_chain(cls, files):
        """
        Build a list of nodes "soft" linked. This means that each has an id
        (an integer value) and possibly a backref which is also an integer.
        Not a truly "linked" list
    
        Returns an array of SimpleNodes
        :rtype : list
        """
        nodes = []
    
        for f in files:
            if not Constants.FILENAME_STANDARD.search(f):
                continue
    
            try:
                my_file = open(os.path.join(Constants.ALTER_DIR, f))
                head = list(islice(my_file, 3))
            except OSError, ex:
                sys.stderr.write("Error opening file '%s'.\n\t=>%s\n" % (os.path.join(Constants.ALTER_DIR, f), ex.message))
                sys.exit(1)
    
            if not MetaDataUtil.parse_direction(head) == 'up':
                continue
    
            meta_data = MetaDataUtil.parse_meta(head)
    
            if not 'ref' in meta_data:
                continue
    
            node = SimpleNode(filename=f, id=meta_data['ref'])
            if 'backref' in meta_data:
                node.backref = meta_data['backref']

            node.meta = meta_data
    
            nodes.append(node)
    
        return nodes


    @classmethod
    def __build_and_validate_linked_list(cls, nodes):
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
