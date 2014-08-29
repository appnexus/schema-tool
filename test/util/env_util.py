# stdlib imports
import os
import shutil
import sys
import tempfile

# src imports
import_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../src')
sys.path.append(import_path)
from command import NewCommand, CommandContext
from constants import Constants


class EnvironmentUtil:

    @classmethod
    def setup_fresh_test_env(cls):
        cls.env_folder = tempfile.mkdtemp()
        os.chdir(cls.env_folder)

        cls.previous_dir = os.getcwd()
        cls.current_dir = cls.env_folder

        Constants.ALTER_DIR = cls.current_dir
    
    @classmethod
    def teardown_fresh_test_env(cls):
        os.chdir(cls.previous_dir)
        cls.current_dir = cls.previous_dir
        shutil.rmtree(cls.env_folder)

        Constants.ALTER_DIR = cls.current_dir

