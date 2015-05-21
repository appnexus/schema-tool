# stdlib imports
import subprocess
import sys

# local imports
from errors import AppliedAlterError

# TODO: Move connection management to schema.py. Instantiate a connection
# before each run() method and close it at the end, using the DB.conn() method.

class Db(object):
    """
    Do not instantiate directly.
    Contains all the methods related to initialization of the environment that the
    script will be running in.
    """

    @classmethod
    def new(cls, config):
        cls.config = config
        cls.conn_initialized = False

        return cls

    @classmethod
    def init(cls, force=False):
        """
        Make sure that the table to track revisions is there.
        """

        if force:
            sys.stdout.write('Removing existing history')
            cls.drop_revision()

        sys.stdout.write('Creating revision database\n')
        cls.create_revision()
        sys.stdout.write('Creating history table\n')
        cls.create_history()
        sys.stdout.write('DB Initialized\n')

    @classmethod
    def run_up(cls, alter, force=False, verbose=False):
        """
        Run the up-alter against the DB
        """
        sys.stdout.write('Running alter: %s\n' % alter.filename)
        filename = alter.abs_filename()
        cls._run_file(filename=filename, exit_on_error=not force, verbose=verbose)

        cls.append_commit(ref=alter.id)

    @classmethod
    def run_down(cls, alter, force=False, verbose=False):
        """
        Run the down-alter against the DB
        """
        sys.stdout.write('Running alter: %s\n' % alter.down_filename())
        filename = alter.abs_filename(direction='down')
        cls._run_file(filename=filename, exit_on_error=not force, verbose=verbose)

        cls.remove_commit(ref=alter.id)

    @classmethod
    def _run_file(cls, filename, exit_on_error=True, verbose=False):
        # Used for testing to simulate an error in the running of an alter file
        if getattr(cls, 'auto_throw_error', False) and 'error' in filename:
            command, my_env, stdin_stream = cls.run_file_cmd_with_error(filename)
        else:
            command, my_env, stdin_stream = cls.run_file_cmd(filename)

        if stdin_stream:
            proc = subprocess.Popen(command,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    env=my_env)

            script = open(filename)
            out, err = proc.communicate(script.read())
        else:
            proc = subprocess.Popen(command,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    env=my_env)
            out, err = proc.communicate()

        if err:
            sys.stderr.write("\n----------------------\n")
            sys.stderr.write(out.rstrip())
            sys.stderr.write(err.rstrip())
            sys.stderr.write("\n----------------------\n")
        if not proc.returncode == 0:
            sys.stderr.write('Error')
            if verbose:
                sys.stderr.write("\n----------------------\n")
                sys.stderr.write(out.rstrip())
                sys.stderr.write(err.rstrip())
                sys.stderr.write("\n----------------------\n")
            sys.stderr.write("\n")
            if exit_on_error:
                raise AppliedAlterError('%s execution unsuccessful' % filename)

    @classmethod
    def get_applied_alters(cls):
        results = cls.execute('SELECT alter_hash FROM %s' % cls.full_table_name)
        alters_hashes = [result[0] for result in results]
        return alters_hashes
