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
    def parse_env(cls, envlist_str):
        result = []
        for i in envlist_str.split(','):
            i_stripped = i.strip()
            match = re.match(Constants.ENV_NAME_STANDARD, i_stripped)
            if match is not None:
                result.append(match.group(0))
            else:
                raise Exception('Invalid environment name: \'%s\'' % i_stripped)
        return result

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
    def parse_meta(cls, file_contents):
        """
        Given the file contents (all of it) parse the meta-data and what have
        you. Really just the first few lines until a non-empty, non-space, non-
        comment line is reached. This will return the refs (this-ref and back-ref)
        as well as any other meta-data (env, author, etc.)

        Return a dict of key-value pairs where the key is the meta-data key and the
        value is the meta-data value. Ex:
        { "ref": 1234, "backref": 123, "env": "prod" }
        """
        meta = {}
        valid_line = re.compile('^\s*--|^\s*$')
        for line in file_contents:
            if valid_line.match(line) == None:
                break
            key, value = cls.__parse_key(line)
            if key and value:
                meta[key] = value

        return meta

    @classmethod
    def __parse_key(cls, line):
        """
        Given a line, parse a key-value pair out of it. Key value pairs are seen
        as SQL comments followed by some string and a ':' that separate the key
        and value.  Some examples are:

          -- one: two
          -- _three3: four
          -- 5-9: 10-20

        Returns a 2-tuple of the key-value pair. Note that whitespace is trimmed
        off of the beginning and end of keys and values
        """
        comment_regex = re.compile('\s*--\s*')
        line = comment_regex.sub('', line)

        key_value_regex = re.compile('^([a-zA-Z0-9\-_]+\s*):(.*)$')
        match = key_value_regex.match(line)

        if match:
            key   = match.groups()[0].strip()
            value = match.groups()[1].strip()
        else:
            key   = None
            value = None

        return (key, value)
