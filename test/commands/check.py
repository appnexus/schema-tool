# stdlib imports
import os
import sys
import unittest

# src imports
import_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../schematool')
sys.path.append(import_path)
from command import DownCommand, CommandContext, NewCommand
from command import UpCommand, CheckCommand
from errors import MissingDownAlterError, MissingUpAlterError
from util import ChainUtil

# test util imports
import_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../util')
sys.path.append(import_path)
from alter_util import AlterUtil
from env_util import EnvironmentUtil
from test_util import make_argv

class CheckTest(unittest.TestCase):

    def setUp(self):
        EnvironmentUtil.setup_fresh_test_env()
        self.context = CommandContext.via({
          'type': 'memory-db'})
        self.downCommand = DownCommand(self.context)
        self.newCommand = NewCommand(self.context)
        self.upCommand  = UpCommand(self.context)
        self.checkCommand  = CheckCommand(self.context)

    def tearDown(self):
        EnvironmentUtil.teardown_fresh_test_env()

    def test_valid_chain(self):
        AlterUtil.create_alters([1, 2])
        AlterUtil.run_alters()
        sys.argv = make_argv([])
        self.checkCommand.run()

    def help_test_missing_alter(self, search, error):
        AlterUtil.create_alters([1])
        AlterUtil.run_alters()

        alter_files = ChainUtil.get_alter_files()
        self.assertEqual(len(alter_files), 2) # up and down
        os.remove([i for i in alter_files if search in i].pop())

        try:
            sys.argv = make_argv([])
            self.checkCommand.run()
        except error:
            pass

    def test_missing_up_alter(self):
        return self.help_test_missing_alter('-up', MissingUpAlterError)

    def test_missing_down_alter(self):
        return self.help_test_missing_alter('-down', MissingDownAlterError)




if __name__ == '__main__':
    unittest.main()
