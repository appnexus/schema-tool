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
