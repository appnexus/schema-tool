# stdlib imports
import os
import sys
import unittest

# src imports
import_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../schematool')
sys.path.append(import_path)
from command import CommandContext, UpCommand
from db import MemoryDb
from errors import MissingRefError, AppliedAlterError

# test util imports
import_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../util')
sys.path.append(import_path)
from env_util import EnvironmentUtil
from alter_util import AlterUtil
from test_util import make_argv

class UpTest(unittest.TestCase):

    def setUp(self):
        EnvironmentUtil.setup_fresh_test_env()
        self.context = CommandContext.via({
          'type': 'memory-db'})
        self.upCommand  = UpCommand(self.context)

    def tearDown(self):
        EnvironmentUtil.teardown_fresh_test_env()

    def test_no_arg_does_all_current_alters_when_none(self):
        self.assertEqual(len(MemoryDb.data), 0)
        sys.argv = make_argv([])
        self.upCommand.run()
        self.assertEqual(len(MemoryDb.data), 0)

    def test_no_arg_does_all_current_alters_when_alters(self):
        AlterUtil.create_alters([1])
        sys.argv = make_argv([])
        self.upCommand.run()
        self.assertEqual(len(MemoryDb.data), 1)

    def test_ref_does_all_alters_including_ref(self):
        id1, id2 = AlterUtil.create_alters([1,2])
        sys.argv = make_argv([str(id1)])
        self.upCommand.run()
        self.assertEqual(len(MemoryDb.data), 1)

    def test_ref_does_nothing_when_ref_doesnt_exist(self):
        AlterUtil.create_alters([1])
        sys.argv = make_argv([str(10)])
        try:
            self.upCommand.run()
        except MissingRefError:
            pass

    def test_n_option_runs_up_given_number_of_alters(self):
        AlterUtil.create_alters([1, 2, 3, 4])
        sys.argv = make_argv(['-n2'])
        self.upCommand.run()
        self.assertEqual(len(MemoryDb.data), 2)

    def test_up_resumes_after_last_executed_alter(self):
        AlterUtil.create_alters([1])
        sys.argv = make_argv([])
        self.upCommand.run()
        self.assertEqual(len(MemoryDb.data), 1)

        AlterUtil.create_alters([2])
        sys.argv = make_argv([])
        self.upCommand.run()
        self.assertEqual(len(MemoryDb.data), 2)

    def test_stop_on_error(self):
        AlterUtil.create_alters([1, 'error', 2])
        sys.argv = make_argv([])
        try:
            self.upCommand.run()
        except AppliedAlterError:
            pass
        self.assertEqual(len(MemoryDb.data), 1)

    def test_continue_on_error_with_force(self):
        AlterUtil.create_alters([1, 'error', 2])
        sys.argv = make_argv(['-f'])
        self.upCommand.run()
        self.assertEqual(len(MemoryDb.data), 3)


if __name__ == '__main__':
    unittest.main()
