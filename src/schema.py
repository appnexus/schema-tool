#!/usr/bin/env python2.7

# File: schema
# Author: John Murray <jmurray@appnexus.com>
#
# For more information on how to use the script, call with the '-h'
# option. Also see the accompanying 'readme.md' file in the top-level
# of the project.


import sys

(v_major, v_minor, _, _, _) = sys.version_info
if v_major != 2 or (v_major == 2 and v_minor != 7):
    sys.stderr.write("Warning: Tool only tested against 2.7. Results may vary" +
                     " with older versions.\n\n")
if v_major == 2 and v_minor < 6:
    import simplejson as json
else:
    import json

from optparse import OptionParser
from traceback import print_exc

# loal imports
from command import *


def main(config):
    """
    Determine what command is being called and dispatch it to the appropriate
    handler. If the command is unknown or the '-h' or '-v' flag has been given, 
    display help-file or version-info, respectively.
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
        "  version     Shows current version of tool",
        "  help        Show this help message and exit"
    ]
    usage = "schema command [options]\n\nCommands:\n" + ("\n".join(commands))
    parser = OptionParser(usage=usage)

    if len(sys.argv) == 1:
        sys.stderr.write("Error: No commands or options given, view -h for each\n" +
                         "       command for more information\n\n")
        parser.print_help();
        sys.exit(1)
    if sys.argv[1] in ['-v', '--version', 'version']:
        sys.stderr.write('Version: %s\n' % Constants.VERSION)
        sys.exit(0)
    if sys.argv[1] in ['-h', '--help', 'help']:
        parser.print_help()
        sys.exit(0)

    # check if the command given is valid and dispatch appropriately
    user_command = sys.argv[1]
    if user_command in [c['command'] for c in Constants.COMMANDS]:
        # strip command-name from arguments
        sys.argv = sys.argv[1:]

        # Create context and select handler and attempt to dispatch
        context = CommandContext.via(config)
        handler = [c['handler'] for c in Constants.COMMANDS if c['command'] == user_command][0]
        try:
            globals()[handler](context).run()
        except SystemExit:
            sys.exit(1)
        except EnvironmentError, er:
            sys.stderr.write(
                "An exception has occurred... Sorry. You should file a ticket in\nour issue tracker: %s\n\n" % (
                    Constants.ISSUE_URL))
            sys.stderr.write("Error: %s, %s\n\n" % (er.errno, er.strerror))
            sys.exit(1)
        except Exception, ex:
            sys.stderr.write(
                "An exception has occurred... Sorry. You should file a ticket in\nour issue tracker: %s\n\n" % (
                    Constants.ISSUE_URL))
            sys.stderr.write("Error: %s\n\n" % ex)
            print_exc()
            sys.exit(1)
    else:
        sys.stderr.write("No command '%s' defined\n\n" % sys.argv[1])
        parser.print_help()

def load_config():
    """
    Read the config file and return the values
    """
    try:
        config_file = open(Constants.CONFIG_FILE, 'r')
        try:
            config = json.load(config_file)
        except ValueError, ex:
            sys.stderr.write("Could not parse config file: %s\n" % ex.message)
            sys.exit(1)
    except IOError, ex:
        sys.stderr.write("Error reading config: %s\n" % ex.strerror)
        sys.stderr.write("Tried reading: %s\n" % Constants.CONFIG_FILE)
        sys.exit(1)
    return config



# Start the script
if __name__ == "__main__":
    config = load_config()
    main(config)
