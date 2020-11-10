class yaerror(Exception):
    pass

class MappingError(yaerror):
    def __init__(self, msg, node):
        self.msg = msg
        self.node = node

    def __str__(self):
        return '{}\n{}'.format(self.msg, self.node.start_mark)

class NoMatchingType(MappingError):
    def __init__(self, node):
        super().__init__('Found no matching type', node)
