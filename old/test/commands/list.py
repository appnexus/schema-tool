# stdlib imports
import os
import sys
import unittest

# src imports
import_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../schematool')
sys.path.append(import_path)
from command import CommandContext, ListCommand

# test util imports
import_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../util')
sys.path.append(import_path)
from alter_util import AlterUtil
from env_util import EnvironmentUtil
from test_util import make_argv

class ListTest(unittest.TestCase):

    def setUp(self):
        EnvironmentUtil.setup_fresh_test_env()
        self.context = CommandContext.via({
          'type': 'memory-db'})
        self.listCommand = ListCommand(self.context)

    def tearDown(self):
        EnvironmentUtil.teardown_fresh_test_env()

    def test_order(self):
        id1, id2 = AlterUtil.create_alters([1, 2])
        AlterUtil.run_alters()
        sys.argv = make_argv([])
        result = self.listCommand.run()
        self.assertEqual([id1, id2], result)

    def test_order_reverse(self):
        id1, id2 = AlterUtil.create_alters([1, 2])
        AlterUtil.run_alters()
        sys.argv = make_argv(['-r'])
        result = self.listCommand.run()
        self.assertEqual([id2, id1], result)


if __name__ == '__main__':
    unittest.main()
