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

''' Hierarchy of types to build yamap schemas out of. '''

import abc
import collections
import copy
import re
import ruamel
import typing

from dataclasses import (
    dataclass,
    field,
    fields as get_dataclass_fields,
    InitVar as initvar,
)

from .mapper import load_and_map
from .errors import MappingError
from .util import (
    zip_first,
    mkobj,
    re_tuple,
    pair,
    squasheddict,
    unfreeze,
)


class yatype(abc.ABC):
    ''' Abstract base class for all types to derive from. '''

    def copy(self, **kwargs):
        ''' Helper method for creating copies of instances. Will modify
            values of frozen fields. '''

        new = copy.copy(self)
        with unfreeze(new) as unfrozen:
            for fld in get_dataclass_fields(new):
                if fld.name not in kwargs:
                    continue
                unfrozen[fld.name] = kwargs[fld.name]
        return new

class yamatchable(abc.ABC):
    @abc.abstractmethod
    def matches(self, node, throw=True):
        pass

class yaresolvable(abc.ABC):
    @abc.abstractmethod
    def is_branch(self, node):
        pass

    @abc.abstractmethod
    def resolve(self, value):
        pass

class yatreeish(yaresolvable):
    @abc.abstractmethod
    def match_children(self, node):
        pass

    def is_branch(self, node):
        return True


@dataclass(frozen=True)
class yaoneof(yatype,yamatchable):
    types: typing.Tuple[yatype, ...] = field(init=False, default=())

    def __init__(self, *types):
        with unfreeze(self) as unfrozen:
            unfrozen.types = tuple(map(mkobj, types))

    def __iter__(self):
        return iter(self.types)

    def matches(self, node, throw=True):
        for tpe in self.types:
            res = tpe.matches(node, throw=False)
            if res is not None:
                return res

        if throw:
            raise MappingError()

        return None

@dataclass(frozen=True)
class yaexpand(yatype,yatreeish):
    key: str
    value_type: yatype
    type: typing.Callable[[str, typing.Any], typing.Any] = pair

    def match_children(self, node):
        return [(node, self.value_type.matches(node))]

    def resolve(self, value):
        return self.type(self.key, value[0])


@dataclass(frozen=True)
class yanode_data:
    tag: initvar[str] = None
    tags: initvar[typing.Tuple[str, ...]] = ()
    type: typing.Optional[typing.Callable[..., typing.Any]] = None
    re_tags: typing.Tuple[re.Pattern, ...] = field(init=False, default=())

class yanode(yanode_data,yatype,yaresolvable,yamatchable):
    def __post_init__(self, tag, tags):
        if tag or tags:
            with unfreeze(self) as unfrozen:
                unfrozen.re_tags = re_tuple(*filter(None, tags + (tag,)))

    def matches(self, node, throw=True):
        for tag in self.re_tags:
            if tag.fullmatch(node.tag):
                return self

        if throw:
            raise MappingError()

        return None

    def load(self, stream):
        return load_and_map(stream, self)

    def resolve(self, value):
        return value if self.type is None else self.type(value)

class yaleafnode(yanode):
    @abc.abstractmethod
    def construct(self, constructor, node):
        pass

    def is_branch(self, node):
        return False

class yabranchnode(yanode,yatreeish):
    pass


@dataclass(frozen=True)
class yascalar(yaleafnode):
    re_tags: typing.Tuple[re.Pattern, ...] = re_tuple(
        'tag:yaml.org,2002:str',
        'tag:yaml.org,2002:int',
    )
    construct: typing.Callable[
        [ruamel.yaml.constructor.BaseConstructor, ruamel.yaml.nodes.Node],
        typing.Any
    ] = lambda constructor, node: constructor.construct_scalar(node)

@dataclass(frozen=True)
class yastr(yascalar):
    re_tags: typing.Tuple[re.Pattern, ...] = re_tuple(
        'tag:yaml.org,2002:str',
    )


@dataclass(frozen=True)
class yamap_data:
    re_tags: typing.Tuple[re.Pattern, ...] = re_tuple(
        'tag:yaml.org,2002:map',
    )

class yamap(yamap_data,yabranchnode):
    pass

@dataclass(frozen=True)
class yadict(yamap):

    @dataclass(frozen=True)
    class typeitem:
        regex: str
        type: yatype
        resolve: typing.Callable[[str, typing.Any], typing.Any] = pair
        required: bool = False
        repeat: bool = False

        def __post_init__(self):
            with unfreeze(self) as unfrozen:
                unfrozen.regex = re.compile(unfrozen.regex)
                unfrozen.type = mkobj(unfrozen.type)

        def matches(self, key, value):
            if not self.regex.fullmatch(key):
                return None
            return self.type.matches(value, throw=False)

    type: typing.Optional[typing.Callable[[typing.Any], typing.Any]] = None
    squash: bool = False
    types: typing.Tuple[typeitem, ...] = field(init=False, default=())

    def __post_init__(self, tag, tags):
        super().__post_init__(tag, tags)
        with unfreeze(self) as unfrozen:
            if unfrozen.type is None:
                unfrozen.type = squasheddict if unfrozen.squash else dict

    def match_children(self, node):
        result = []
        counts = collections.defaultdict(lambda: 0)

        for key,value in node.value:
            if key.tag != 'tag:yaml.org,2002:str':
                raise Exception()

            key = key.value
            tpe,value_tpe = zip_first(
                 # pylint: disable=cell-var-from-loop
                lambda tpe: tpe.matches(key, value),
                self.types
            )

            if tpe is None:
                raise Exception('no matching type')

            counts[tpe] += 1
            result.append((value, yaexpand(key, value_tpe, tpe.resolve)))

        for tpe in self.types:
            if tpe.required and not counts[tpe]:
                raise Exception('required missing')

        return result

    def copy(self, *args, **kwargs):
        return super().copy(
            types = self.types + (self.typeitem(*args, **kwargs),)
        )

    def optional(self, regex, schema, type=pair):
        return self.copy(regex, schema, resolve=type)

    def required(self, regex, schema, type=pair):
        return self.copy(regex, schema, resolve=type, required=True)

    def zero_or_more(self, regex, schema, type=pair):
        return self.copy(regex, schema, resolve=type, repeat=True)

    def one_or_more(self, regex, schema, type=pair):
        return self.copy(regex, schema, resolve=type, repeat=True, required=True)


@dataclass(frozen=True)
class yalist(yabranchnode):
    re_tags: typing.Tuple[re.Pattern, ...] = re_tuple(
        'tag:yaml.org,2002:seq',
    )
    types: yaoneof = field(init=False, default_factory=yaoneof)

    def match_children(self, node):
        return [
            (item, self.types.matches(item))
            for item in node.value
        ]

    def can_contain(self, value):
        return self.copy(types = yaoneof(*self.types, value))


__all__ = (
    'yaoneof',
    'yascalar',
    'yastr',
    'yadict',
    'yalist',
)
