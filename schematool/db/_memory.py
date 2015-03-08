# stdlib imports
import copy

from db import Db

class MemoryDb(Db):
    @classmethod
    def new(cls, config):
        super(MemoryDb, cls).new(config)

        cls.data = []
        cls.id   = 0
        cls.auto_throw_error = True

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
        return [d[1] for d in cls.data]

    @classmethod
    def append_commit(cls, ref):
        cls.id += 1
        cls.data.append([cls.id, ref, None])

    @classmethod
    def get_append_commit_query(cls, _):
        return "n/a for memory-db"

    @classmethod
    def remove_commit(cls, ref):
        to_remove = [d for d in cls.data if d[1] == ref]
        if len(to_remove) > 0:
            cls.data.remove(to_remove[0])
        return True

    @classmethod
    def get_remove_commit_query(cls, _):
        return "n/a for memory-db"

    @classmethod
    def create_history(cls):
        return True

    @classmethod
    def conn(cls):
        return cls

    @classmethod
    def run_file_cmd(cls):
        return ['/bin/true'], None

    @classmethod
    def run_file_cmd_with_error(cls):
        return ['/bin/false'], None
