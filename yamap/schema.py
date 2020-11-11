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

from dataclasses import (
    dataclass,
    field,
    fields as get_dataclass_fields,
    InitVar as initvar,
)
from contextlib import (
    suppress,
)
from ruamel.yaml.nodes import (
    Node as YAMLNode,
)
from ruamel.yaml.constructor import (
    BaseConstructor,
)
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from .mapper import load_and_map
from .errors import (
    MappingError,
    NoMatchingType,
)
from .util import (
    zip_first,
    mkobj,
    re_tuple,
    pair,
    squasheddict,
    unfreeze,
)

# type aliases
MatchResult = Union['yaleafnode','yabranchnode']
Mappable = Union['yaoneof', 'yaexpand', MatchResult]
MappableAndTypes = Union[Mappable, Type['yaoneof'], Type['yaexpand'],
                         Type['yaleafnode'], Type['yabranchnode']]
PairlikeCallable = Callable[[str, Any], Any]
ConstructorCallable = Callable[[BaseConstructor, YAMLNode], Any]
EntryKey = Tuple[re.Pattern, Mappable, PairlikeCallable]
RegexTuple = Tuple[re.Pattern, ...]
MatchChildrenResult = List[Tuple[YAMLNode, MatchResult]]
EntryMatchResult = Optional[Tuple[str, MatchResult, PairlikeCallable]]
S = TypeVar('S', bound='yanode', covariant=True)
T = TypeVar('T')

class yatype(abc.ABC):
    ''' Abstract base class for all types to derive from. '''

    def copy(self: T, **kwargs) -> T:
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
    def matches(self, node: YAMLNode) -> MatchResult:
        pass

class yaresolvable(abc.ABC):
    @abc.abstractmethod
    def is_branch(self, node: YAMLNode) -> bool:
        pass

    @abc.abstractmethod
    def resolve(self, value: Any) -> Any:
        pass

class yatreeish(yaresolvable):
    @abc.abstractmethod
    def match_children(self, node: YAMLNode) -> MatchChildrenResult:
        pass

    def is_branch(self, node: YAMLNode) -> bool:
        return True


@dataclass(frozen=True)
class yaoneof(yatype,yamatchable):
    entries: Tuple[Mappable, ...] = field(init=False, default=())

    def __init__(self, *entries: List[MappableAndTypes]) -> None:
        with unfreeze(self) as unfrozen:
            unfrozen.entries = tuple(map(mkobj, entries))

    def __iter__(self) -> Iterator[yatype]:
        return iter(self.entries)

    def matches(self, node: YAMLNode) -> MatchResult:
        for entry in self.entries:
            with suppress(NoMatchingType):
                return entry.matches(node)

        raise NoMatchingType(node)

    def case(self, entry: MappableAndTypes):
        return self.copy(entries = self.entries + (mkobj(entry),))

@dataclass(frozen=True)
class yaexpand(yatype,yatreeish,yamatchable):
    key: str
    value_schema: Mappable
    type: PairlikeCallable = pair

    def matches(self, node: YAMLNode) -> MatchResult:
        return self.value_schema.matches(node)

    def match_children(self, node: YAMLNode) -> MatchChildrenResult:
        return [(node, self.value_schema.matches(node))]

    def resolve(self, value: List[Any]) -> Any:
        return self.type(self.key, value[0]) # type: ignore


@dataclass(frozen=True)
class yanode_data:
    tag: initvar[str] = None
    tags: initvar[Tuple[str, ...]] = ()
    type: Optional[Callable[..., Any]] = None
    re_tags: RegexTuple = field(init=False, default=())

class yanode(yanode_data,yatype,yaresolvable,yamatchable):
    def __post_init__(self, tag: str, tags: Tuple[str, ...]) -> None:
        if tag or tags:
            with unfreeze(self) as unfrozen:
                unfrozen.re_tags = re_tuple(*filter(None, tags + (tag,)))

    def matches(self, node: YAMLNode) -> MatchResult:
        for tag in self.re_tags:
            if tag.fullmatch(node.tag):
                return self # type: ignore

        raise NoMatchingType(node)

    def resolve(self, value: Any) -> Any:
        return value if self.type is None else self.type(value)

class yaleafnode(yanode):
    @abc.abstractmethod
    def construct(self, constructor: BaseConstructor, node: YAMLNode) -> Any:
        pass

    def is_branch(self, node: YAMLNode) -> bool:
        return False

    def load(self, stream: Any) -> Any:
        return load_and_map(stream, self)


class yabranchnode(yanode,yatreeish):
    def load(self, stream: Any) -> Any:
        return load_and_map(stream, self)


def as_scalar(constructor: BaseConstructor, node: YAMLNode) -> Any:
    if node.tag == 'tag:yaml.org,2002:null':
        return None
    return constructor.construct_scalar(node)

@dataclass(frozen=True)
class yascalar(yaleafnode):
    re_tags: RegexTuple = re_tuple(
        'tag:yaml.org,2002:str',
        'tag:yaml.org,2002:int',
        'tag:yaml.org,2002:null',
    )
    construct: ConstructorCallable = as_scalar # type: ignore

@dataclass(frozen=True)
class yastr(yascalar):
    re_tags: RegexTuple = re_tuple('tag:yaml.org,2002:str')

@dataclass(frozen=True)
class yanull(yascalar):
    re_tags: RegexTuple = re_tuple('tag:yaml.org,2002:null')


@dataclass(frozen=True)
class yaentry(yatype):
    required: bool = False
    repeat: bool = False
    keys: Tuple[EntryKey, ...] = field(init=False, default=())

    def match_item(self, key: str, value: YAMLNode) -> EntryMatchResult:
        for (regex, schema, type) in self.keys:
            if not regex.fullmatch(key):
                continue

            with suppress(NoMatchingType):
                return (key, schema.matches(value), type)

        return None

    def case(self, pattern: str, schema: MappableAndTypes,
                   type: PairlikeCallable = pair) -> 'yaentry':
        return self.copy(
            keys = self.keys + ((re.compile(pattern), mkobj(schema), type),)
        )

    @property
    def keys_repr(self) -> str:
        return '({})'.format(' | '.join(r.pattern for r,s,t in self.keys))

@dataclass(frozen=True)
class yamap(yabranchnode):
    re_tags: RegexTuple = re_tuple('tag:yaml.org,2002:map')
    type: Optional[Callable[[list], Any]] = None
    squash: bool = False
    entries: Tuple[yaentry, ...] = field(init=False, default=())

    def __post_init__(self, tag: str, tags: Tuple[str, ...]) -> None:
        super().__post_init__(tag, tags)
        with unfreeze(self) as unfrozen:
            if unfrozen.type is None:
                unfrozen.type = squasheddict if unfrozen.squash else dict

    def match_children(self, node: YAMLNode) -> MatchChildrenResult:
        result: MatchChildrenResult = []
        counts: Dict[yaentry, int]  = collections.defaultdict(lambda: 0)

        for key_node,value in node.value:
            if key_node.tag != 'tag:yaml.org,2002:str':
                raise MappingError(
                    'Only plain strings supported as mapping keys',
                    key_node
                )

            key = key_node.value
            entry,match = zip_first(
                 # pylint: disable=cell-var-from-loop
                lambda entry: entry.match_item(key, value),
                self.entries
            )

            if entry is None:
                raise NoMatchingType(key_node)

            counts[entry] += 1
            result.append((value, yaexpand(*match))) # type:ignore

        for entry in self.entries:
            if entry.required and not counts[entry]:
                raise MappingError(
                    'Required key {} missing'.format(entry.keys_repr),
                    node
                )

            if not entry.repeat and counts[entry] > 1:
                raise MappingError(
                    'Maximum one of {} allowed'.format(entry.keys_repr),
                    node
                )

        return result

    def entry(self, entry: yaentry) -> 'yamap':
        return self.copy(entries = self.entries + (entry,))

    def case(self, regex: str, schema: MappableAndTypes,
                   type: PairlikeCallable = pair,
                   repeat: bool = False, required: bool = False) -> 'yamap':
        return self.entry(
            yaentry(required=required, repeat=repeat).case(regex, schema, type)
        )

    def zero_or_one(self, regex: str, schema: MappableAndTypes,
                          type: PairlikeCallable = pair) -> 'yamap':
        return self.case(regex, schema, type)

    def exactly_one(self, regex: str, schema: MappableAndTypes,
                          type: PairlikeCallable = pair) -> 'yamap':
        return self.case(regex, schema, type, required=True)

    def zero_or_more(self, regex: str, schema: MappableAndTypes,
                           type: PairlikeCallable = pair) -> 'yamap':
        return self.case(regex, schema, type, repeat=True)

    def one_or_more(self, regex: str, schema: MappableAndTypes,
                          type: PairlikeCallable = pair) -> 'yamap':
        return self.case(regex, schema, type, repeat=True, required=True)


@dataclass(frozen=True)
class yaseq(yabranchnode):
    re_tags: RegexTuple = re_tuple('tag:yaml.org,2002:seq')
    schema: yaoneof = field(init=False, default_factory=yaoneof)

    def match_children(self, node: YAMLNode) -> MatchChildrenResult:
        return [
            (item, self.schema.matches(item))
            for item in node.value
        ]

    def case(self, schema: MappableAndTypes) -> 'yaseq':
        return self.copy(schema = self.schema.case(schema))


__all__ = (
    'yaoneof',
    'yascalar',
    'yastr',
    'yanull',
    'yaentry',
    'yamap',
    'yaseq',
)
