# stdlib imports
import os
import sys
from time import sleep

# src imports
import_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../src')
sys.path.append(import_path)
from command import NewCommand, CommandContext, UpCommand
from util import ChainUtil


class AlterUtil(object):
    initialized = False

    @classmethod
    def init(cls):
        if not cls.initialized:
            cls.context = CommandContext.via({
              'type': 'memory-db'})
            cls.newCommand = NewCommand(cls.context)
            cls.upCommand  = UpCommand(cls.context)
            cls.initialized = True

    @classmethod
    def create_alter(cls, name):
        cls.init()
        sys.argv = ['', '-f', str(name)]
        return cls.newCommand.run()

    @classmethod
    def create_alters(cls, names):
        result = []
        cls.init()
        for name in names:
            inner = cls.create_alter(name)
            result.append(inner)
            sleep(0.1)
        return result

    @classmethod
    def run_alters(cls):
        cls.init()
        sys.argv = ['']
        cls.upCommand.run()
        tail = ChainUtil.build_chain()

        ids = []
        while tail is not None and tail.backref is not None:
            ids.append(tail.id)
            tail = tail.backref

        return ids
