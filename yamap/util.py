# Copyright 2020 Florian Wagner <florian@wagner-flo.net>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

''' Just a bunch of unrealated helper functions not fitting
    elsewhere. '''

import contextlib
import inspect
import re
import types

def zip_first(pred, iterable):
    ''' Evaluate pred(item) for each item in iterable until this call's
        result is a True value, then return (item, pred(item). If
        iterable is exhausted beforehand return (None, None). '''
    for first in iterable:
        second = pred(first)
        if second:
            return (first, second)

    return (None, None)

def mkobj(cls_or_instance):
    ''' If cls_or_instance is a class then return cls_or_instance()
        otherwise return cls_or_instance. '''
    if inspect.isclass(cls_or_instance):
        return cls_or_instance()
    return cls_or_instance

def re_tuple(*args):
    ''' Compile all arguments as regex patterns and return as tuple. '''
    return tuple(map(re.compile, args))

class pair(tuple):
    ''' Helper class for creating new two-element tuples with a nicer
        constructor. It will not create an instance of pair, but simply
        return the tuple (a, b).'''

    def __new__(cls, a, b):
        return (a, b)

class squasheddict:
    ''' Helper class for turning one-element dictionaries into their
        single value. '''

    def __new__(cls, items):
        if len(items) == 1:
            return items[0]
        if len(items) > 1:
            raise Exception()
        return None

@contextlib.contextmanager
def unfreeze(obj):
    ''' Context manager to clarify code that modifies fields of frozen
        dataclasses. Basically a glorified object.__setattr__. '''

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
