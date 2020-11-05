import inspect

def zip_first(pred, iterable):
    for first in iterable:
        second = pred(first)
        if second:
            return (first, second)

    return (None, None)

def mkobj(cls_or_instance):
    if inspect.isclass(cls_or_instance):
        return cls_or_instance()
    return cls_or_instance

class pair(tuple):
    def __new__(cls, a, b):
        return (a, b)
