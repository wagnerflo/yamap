from . import schema

__all__ = ()

for mod in (schema,):
    for name in mod.__all__:
        globals()[name] = getattr(mod, name)

    __all__ = __all__ + mod.__all__
