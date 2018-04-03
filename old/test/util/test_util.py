def make_argv(argv):
    # sys.argv[0] is the name of the executable - i.e. "foo" in "./foo bar".
    # Since schematool methods receive args from the command line, correctly
    # mocking sys.argv requires inserting a dummy value at index zero.
    return [''] + argv
