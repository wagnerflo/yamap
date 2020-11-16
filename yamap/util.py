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

from __future__ import annotations

import contextlib
import functools
import inspect
import types

from typing import (
    Any,
    Callable,
    Iterable,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    overload,
)

from ruamel.yaml.nodes import Node as YAMLNode
from ruamel.yaml.constructor import SafeConstructor

Object = TypeVar('Object', bound=object)
A = TypeVar('A')
B = TypeVar('B')

def zip_first(pred: Callable[[Any], Any], iterable: Iterable) -> Tuple[Any, Any]:
    ''' Evaluate pred(item) for each item in iterable until this call's
        result is a True value, then return (item, pred(item). If
        iterable is exhausted beforehand return (None, None). '''
    for first in iterable:
        second = pred(first)
        if second:
            return (first, second)

    return (None, None)

@overload
def mkobj(cls_or_instance: Type[Object]) -> Object:
    pass

@overload
def mkobj(cls_or_instance: Object) -> Object:
    pass

def mkobj(cls_or_instance):
    ''' If cls_or_instance is a class then return cls_or_instance()
        otherwise return cls_or_instance. '''
    if inspect.isclass(cls_or_instance):
        return cls_or_instance()
    return cls_or_instance

def pair(a: A, b: B) -> Tuple[A, B]:
    ''' Helper function for creating new two-element tuples. '''
    return (a, b)

def identity(a: A) -> A:
    ''' Helper implementing the identity function. '''
    return a

def squashed(callable: Callable[[A], B]) -> Callable[[Sequence[A]], B]:
    ''' Helper function wrapper for turning one-element dictionaries
        into their single value and unpacking it. '''
    @functools.wraps(callable)
    def squash(items: Sequence[A]) -> B:
        if len(items) == 1:
            return callable(items[0])
        raise RuntimeError('Not exactly one element')
    return squash

def unpacked_map(callable: Callable[..., B]) -> Callable[[Sequence[Tuple[str, A]]], B]:
    ''' Helper function wrapper for unpacking a squence of two element
        tuples as keyword arguments of the wrapped function. '''
    @functools.wraps(callable)
    def unpack(items: Sequence[Tuple[str, A]]) -> B:
        return callable(**dict(items))
    return unpack

def unpacked_seq(callable: Callable[..., B]) -> Callable[[Sequence[A]], B]:
    ''' Helper function wrapper for unpacking a squence as postitional
        arguments of the wrapped function. '''
    @functools.wraps(callable)
    def unpack(items: Sequence[A]) -> B:
        return callable(*items)
    return unpack

def as_scalar(constructor: SafeConstructor, node: YAMLNode) -> Any:
    ''' Helper function to turn YAML scalars into Python objects. '''
    if node.tag == 'tag:yaml.org,2002:null':
        return None
    if node.tag == 'tag:yaml.org,2002:bool':
        return constructor.construct_yaml_bool(node)
    if node.tag == 'tag:yaml.org,2002:float':
        return constructor.construct_yaml_float(node)
    if node.tag == 'tag:yaml.org,2002:int':
        return constructor.construct_yaml_int(node)
    return constructor.construct_scalar(node)

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
