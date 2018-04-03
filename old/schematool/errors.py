class MissingDownAlterError(Exception):
    pass

class MissingUpAlterError(Exception):
    pass

class MissingRefError(Exception):
    pass

class AppliedAlterError(Exception):
    pass

class InvalidDBTypeError(Exception):
    pass

class DbError(Exception):
    pass

class ConfigFileError(Exception):
    pass

class MultipleDownAltersError(Exception):
    pass

class ReadError(Exception):
    pass

class WriteError(Exception):
    pass

class OptionsError(Exception):
    pass

class ArgsError(Exception):
    pass

class DuplicateRefsError(Exception):
    pass

class HeadError(Exception):
    pass

class CircularRefError(Exception):
    pass

class InitError(Exception):
    pass
