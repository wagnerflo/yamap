import contextlib
import inspect
import types

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

@contextlib.contextmanager
def unfreeze(obj):
    cls = types.new_class(
        name = obj.__class__.__name__,
        exec_body = lambda ns: ns.update({
            '__getattr__': lambda s,k: getattr(obj, k),
            '__setattr__': lambda s,k,v: object.__setattr__(obj, k, v),
            '__setitem__': lambda s,k,v: object.__setattr__(obj, k, v),
            '__module__': obj.__module__,
            '__slots__': (),
        })
    )
    yield cls()
