#stdlib imports
import os
import sys
import unittest
from time import sleep

# src imports
import_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../src')
sys.path.append(import_path)
from command import NewCommand, CommandContext
from util import ChainUtil

# test util imports
import_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../util')
sys.path.append(import_path)
from env_util import EnvironmentUtil

class NewTest(unittest.TestCase):

    def setUp(self):
        EnvironmentUtil.setup_fresh_test_env()
        self.context = CommandContext.via({
          'type': 'memory-db'})
        self.commandObj = NewCommand(self.context)

    def tearDown(self):
        EnvironmentUtil.teardown_fresh_test_env()

    def test_create_down(self):
        sys.argv = ['file', '-f', 'test-file']
        self.commandObj.run()
        files = os.walk(os.getcwd()).next()[2]
        files = [f for f in files if not f.find('test-file') == -1]
        files = [f for f in files if not f.find('down') == -1]
        self.assertTrue(len(files) == 1)

    def test_create_up(self):
        sys.argv = ['file', '-f', 'test-file']
        self.commandObj.run()
        files = os.walk(os.getcwd()).next()[2]
        files = [f for f in files if not f.find('test-file') == -1]
        files = [f for f in files if not f.find('up') == -1]
        self.assertTrue(len(files) == 1)

    def test_creates_two_files_on_new(self):
        sys.argv = ['file', '-f', 'test-file']
        self.commandObj.run()
        files = os.walk(os.getcwd()).next()[2]
        files = [f for f in files if not f.find('test-file') == -1]
        self.assertTrue(len(files) == 2)

    def test_create_files_without_name(self):
        sys.argv = ['file']
        self.commandObj.run()
        files = os.walk(os.getcwd()).next()[2]
        files = [f for f in files if not f.find('sql') == -1]
        self.assertTrue(len(files) == 2)

    def test_creates_proper_alter_chain(self):
        sys.argv = ['file', '-f', '1']
        self.commandObj.run()
        sleep(0.15)
        sys.argv = ['file', '-f', '2']
        self.commandObj.run()

        chain_tail = ChainUtil.build_chain()
        self.assertTrue(chain_tail.backref is not None)
        self.assertTrue(chain_tail.backref.backref is None)

    def test_no_backref_on_single_alter(self):
        sys.argv = ['file', '-f', '1']
        self.commandObj.run()
 
        chain_tail = ChainUtil.build_chain()
        self.assertTrue(chain_tail.backref is None)


if __name__ == '__main__':
    unittest.main()
