# stdlib imports
import os
import sys
import unittest

# src imports
import_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../schematool')
sys.path.append(import_path)
from command import CommandContext, DownCommand
from db import MemoryDb
from errors import MissingRefError

# test util imports
import_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../util')
sys.path.append(import_path)
from alter_util import AlterUtil
from env_util import EnvironmentUtil
from test_util import make_argv

class DownTest(unittest.TestCase):

    def setUp(self):
        EnvironmentUtil.setup_fresh_test_env()
        self.context = CommandContext.via({
          'type': 'memory-db'})
        self.downCommand = DownCommand(self.context)

    def tearDown(self):
        EnvironmentUtil.teardown_fresh_test_env()

    def test_all_undoes_all_current_alters_when_none(self):
        self.assertEqual(len(MemoryDb.data), 0)
        sys.argv = make_argv(['all'])
        self.downCommand.run()
        self.assertEqual(len(MemoryDb.data), 0)

    def test_all_undoes_all_current_alters_when_alters(self):
        AlterUtil.create_alters([1])
        AlterUtil.run_alters()
        self.assertEqual(len(MemoryDb.data), 1)

        sys.argv = make_argv(['all'])
        self.downCommand.run()

        self.assertEqual(len(MemoryDb.data), 0)

    def test_ref_undoes_all_alters_including_ref(self):
        AlterUtil.create_alters([1,2,3])
        ids = AlterUtil.run_alters()
        self.assertEqual(len(MemoryDb.data), 3)

        sys.argv = make_argv([str(ids[1])])
        self.downCommand.run()
        self.assertEqual(len(MemoryDb.data), 1)

    def test_ref_undoes_nothing_when_ref_doesnt_exist(self):
        AlterUtil.create_alters([1, 2, 3, 4])
        AlterUtil.run_alters()
        self.assertEqual(len(MemoryDb.data), 4)

        sys.argv = make_argv([str(10)])
        try:
            self.downCommand.run()
        except MissingRefError:
            pass

        self.assertEqual(len(MemoryDb.data), 4)

    def test_base_undoes_all_but_last_when_more_than_one(self):
        AlterUtil.create_alters([1, 2])
        AlterUtil.run_alters()
        self.assertEqual(len(MemoryDb.data), 2)

        sys.argv = make_argv(['base'])
        self.downCommand.run()

        self.assertEqual(len(MemoryDb.data), 1)

    def test_base_undoes_none_when_no_alters(self):
        self.assertEqual(len(MemoryDb.data), 0)

        sys.argv = make_argv(['base'])
        self.downCommand.run()

        self.assertEqual(len(MemoryDb.data), 0)

    def test_base_undoes_none_when_one_alter(self):
        AlterUtil.create_alters([1])
        AlterUtil.run_alters()
        self.assertEqual(len(MemoryDb.data), 1)

        sys.argv = make_argv(['base'])
        self.downCommand.run()

        self.assertEqual(len(MemoryDb.data), 1)

    def test_n_option_runs_down_given_number_of_alters(self):
        AlterUtil.create_alters([1, 2, 3, 4])
        AlterUtil.run_alters()
        self.assertEqual(len(MemoryDb.data), 4)

        sys.argv = make_argv(['-n2'])
        self.downCommand.run()

        self.assertEqual(len(MemoryDb.data), 2)


if __name__ == '__main__':
    unittest.main()
