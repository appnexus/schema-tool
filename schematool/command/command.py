class Command(object):
    """
    The general command object. Does fun stuff...
    """
    def __init__(self, context):
        self.context = context
        self.config = context.config
        self.db = context.db
        self.init_parser()

    def init_parser(self):
        """
        Initialize all option-parsing stuff and store into self.parser
        """
        pass
