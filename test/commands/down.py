# stdlib imports
import os
import sys
from time import sleep
import unittest

# src imports
import_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../schematool')
sys.path.append(import_path)
from command import DownCommand, CommandContext, NewCommand
from command import UpCommand
from util import ChainUtil
from util import System, SystemExit
from db import MemoryDb

# test util imports
import_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../util')
sys.path.append(import_path)
from env_util import EnvironmentUtil
from alter_util import AlterUtil

class DownTest(unittest.TestCase):

    def setUp(self):
        EnvironmentUtil.setup_fresh_test_env()
        self.context = CommandContext.via({
          'type': 'memory-db'})
        self.commandObj = DownCommand(self.context)
        self.newCommand = NewCommand(self.context)
        self.upCommand  = UpCommand(self.context)
        System.set_test(True)

    def tearDown(self):
        EnvironmentUtil.teardown_fresh_test_env()

    def test_all_undoes_all_current_alters_when_none(self):
        self.assertEqual(len(MemoryDb.data), 0)
        sys.argv = ['file', 'all']
        self.commandObj.run()
        self.assertEqual(len(MemoryDb.data), 0)

    def test_all_undoes_all_current_alters_when_alters(self):
        AlterUtil.create_alters([1])
        AlterUtil.run_alters()
        self.assertEqual(len(MemoryDb.data), 1)

        sys.argv = ['file', 'all']
        self.commandObj.run()

        self.assertEqual(len(MemoryDb.data), 0)


    def test_ref_undoes_all_alters_including_ref(self):
        AlterUtil.create_alters([1,2,3])
        ids = AlterUtil.run_alters()
        self.assertEqual(len(MemoryDb.data), 3)

        sys.argv = ['', str(ids[1])]
        self.commandObj.run()
        self.assertEqual(len(MemoryDb.data), 1)

    def test_ref_undoes_nothing_when_ref_doesnt_exist(self):
        AlterUtil.create_alters([1, 2, 3, 4])
        ids = AlterUtil.run_alters()
        self.assertEqual(len(MemoryDb.data), 4)

        sys.argv = ['', str(10)]
        try:
            self.commandObj.run()
        except SystemExit:
            pass

        self.assertEqual(len(MemoryDb.data), 4)

    def test_base_undoes_all_but_last_when_more_than_one(self):
        AlterUtil.create_alters([1, 2])
        ids = AlterUtil.run_alters()
        self.assertEqual(len(MemoryDb.data), 2)

        sys.argv = ['', 'base']
        self.commandObj.run()

        self.assertEqual(len(MemoryDb.data), 1)
    
    def test_base_undoes_none_when_no_alters(self):
        self.assertEqual(len(MemoryDb.data), 0)

        sys.argv = ['', 'base']
        self.commandObj.run()

        self.assertEqual(len(MemoryDb.data), 0)

    def test_base_undoes_none_when_one_alter(self):
        AlterUtil.create_alters([1])
        ids = AlterUtil.run_alters()
        self.assertEqual(len(MemoryDb.data), 1)

        sys.argv = ['', 'base']
        self.commandObj.run()

        self.assertEqual(len(MemoryDb.data), 1)

    def test_n_option_runs_down_given_number_of_alters(self):
        AlterUtil.create_alters([1, 2, 3, 4])
        ids = AlterUtil.run_alters()
        self.assertEqual(len(MemoryDb.data), 4)

        sys.argv = ['', '-n2']
        self.commandObj.run()

        self.assertEqual(len(MemoryDb.data), 2)


if __name__ == '__main__':
    unittest.main()
