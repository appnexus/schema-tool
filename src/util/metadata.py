import re
import sys

from constants import Constants

class MetaDataUtil(object):
    @classmethod
    def parse_direction(cls, head):
        """
        Given the entire head meta-data (an array of strings) parse out
        the direction of the alter (up/down) and return that value.
    
        Returns a string 'up' or 'down' or None if nothing can be parsed
        from the given input
        """
        head = [h.strip() for h in head]
        direction = None
        for line in head:
            direction = cls.__parse_line_for_direction(line) or direction
    
        return direction
    
    
    @classmethod
    def __parse_line_for_direction(cls, line):
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
    
    
    @classmethod
    def parse_meta(cls, head):
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
            (ref, ref_type) = cls.__parse_ref(line)
            if not ref_type == 'none':
                refs[ref_type] = ref
        return refs
    
    
    @classmethod
    def __parse_ref(cls, line):
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

