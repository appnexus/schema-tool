# stdlib imports
import copy
import sys

from db import Db

class MemoryDb(Db):
    @classmethod
    def new(cls, config):
        super(MemoryDb, cls).new(config)

        cls.data = []

        return cls

    @classmethod
    def init_conn(cls):
        pass


    @classmethod
    def drop_revision(cls):
        cls.data = []

    @classmethod 
    def create_revision(cls):
        pass

    @classmethod
    def get_commit_history(cls):
        return copy.copy(cls.data)

    @classmethod
    def get_applied_alters(cls):
        return [d['ref'] for d in cls.data]

    @classmethod
    def append_commit(cls, ref):
        cls.data.append({'ref': ref})

    @classmethod
    def get_append_commit_query(cls, ref):
        return "n/a for memory-db"

    @classmethod
    def remove_commit(cls, ref):
        to_remove = [d for d in cls.data if d['ref'] == ref]
        if len(to_remove) > 0:
            cls.data.remove(to_remove[0])
        return True

    @classmethod
    def get_remove_commit_query(cls, ref):
        return "n/a for memory-db"

    @classmethod
    def create_history(cls):
        return True

    @classmethod
    def conn(cls):
        return cls

    @classmethod
    def run_file_cmd(cls):
        return ['echo'], None
