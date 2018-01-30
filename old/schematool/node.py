import os
import re
import sys

# local imports
from constants import Constants

class SimpleNode(object):
    """
    Represents a simple node within the alter chain. Just makes things
    a little easier and what not.
    """
    def __init__(self, id, filename):
        self.id = id
        self.backref = None
        self.meta = {}
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
            return os.path.join(Constants.ALTER_DIR, self.filename)
        elif direction == 'down':
            return os.path.join(Constants.ALTER_DIR, self.down_filename())
        else:
            sys.stderr.write("%s is not a valid alter-direction" % direction)
            return None
