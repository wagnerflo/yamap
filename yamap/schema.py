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

from __future__ import annotations

from abc import ABC,abstractmethod
from collections import defaultdict
from copy import copy as mkcopy
from dataclasses import (
    dataclass,
    field,
    fields as get_dataclass_fields,
    MISSING, _MISSING_TYPE,
)
from contextlib import suppress
from re import (
    compile as re_compile,
    Pattern as RegexPattern,
)
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from ruamel.yaml.nodes import Node as YAMLNode
from ruamel.yaml.constructor import SafeConstructor

from .mapper import load_and_map
from .errors import MappingError,NoMatchingType,SchemaError
from .util import (
    zip_first,
    mkobj,
    pair,
    squashed,
    unpacked_map,
    unpacked_seq,
    as_scalar,
    unfreeze,
)

# type aliases
T = TypeVar('T')
PairlikeCallable = Callable[[Any, Any], Any]
ConstructCallable = Callable[[SafeConstructor,YAMLNode], Any]
MatchedChildren = Iterable[Tuple[YAMLNode, 'yatype']] # pylint: disable=E1136
EntryMatchResult = Optional[Tuple[str, 'yatype', PairlikeCallable]] # pylint: disable=E1136
Copyable = TypeVar('Copyable', bound='yacopyable')
MatchArgument = Union['yatype', Type['yatype']] # pylint: disable=E1136
OptField = Union[_MISSING_TYPE, T] # pylint: disable=E1136


class yacopyable:
    ''' Mixin for providing schema classes with an easily usable option
        to copy themselves while modifing some fields in the copy. '''

    def copy(self: Copyable, **kwargs) -> Copyable:
        ''' Helper method for creating copies of instances. Will modify
            values of frozen fields. '''

        new = mkcopy(self)
        with unfreeze(new) as unfrozen:
            for fld in get_dataclass_fields(new):
                if fld.name not in kwargs:
                    continue
                unfrozen[fld.name] = kwargs[fld.name]
        return new

class yamatchable(ABC,yacopyable):
    ''' Abstract base class for all types to derive from. At this point
        no actual YAML to object conversion methods are required as this
        might not be a concrete type. See yatype below. '''

    @abstractmethod
    def matches(self, node: YAMLNode) -> yatype:
        ''' Will try to match the given YAML node to to a concrete
            yatype. This needs to be implemented on any and all classes
            in the hierarchy. '''

    def load(self, stream: Any) -> Any:
        ''' Helper method that tries matching the given stream to self. '''
        return load_and_map(stream, self)

class yatype(yamatchable):
    ''' Concrete schema type that represents one or more parts of the
        YAML file. '''

    @abstractmethod
    def construct_leaf(self, constructor: SafeConstructor,
                             node: YAMLNode) -> Any:
        ''' Turns the YAML node into a Python object. Only needs to be
            implemented for leaf nodes (usually scalars or tags that are
            interpreted as such). '''

    @abstractmethod
    def match_children(self, node: YAMLNode) -> Optional[MatchedChildren]:
        ''' Turns the YAML node into a iterable of (node, schema) tuples.
            Needs to be implemented on branching (mapping, sequence) as
            well as leaf nodes. For the latter it must return None. '''

    @abstractmethod
    def resolve(self, value: Any) -> Any:
        ''' Converts the nodes value into an output type. Leaf node
            values are generated by construct_leaf before being run
            through this method. Branch node values by recursivly
            generating the values of all items return by match_children
            before also being passed to this method. '''


@dataclass(frozen=True)
class yaoneof(yamatchable):
    ''' Virtual schema class that represents the an either-or of types
        possible at this point in the hierarchy. '''

    entries: Tuple[yamatchable, ...] = field(init=False, default=())

    def __init__(self, *entries: List[MatchArgument]) -> None:
        with unfreeze(self) as unfrozen:
            unfrozen.entries = tuple(map(mkobj, entries))

    def __iter__(self) -> Iterator[yamatchable]:
        return iter(self.entries)

    def matches(self, node: YAMLNode) -> yatype:
        for entry in self.entries:
            with suppress(NoMatchingType):
                return entry.matches(node)

        raise NoMatchingType(node)

    def case(self, entry: MatchArgument):
        ''' Register an additonal schema type option. '''
        return self.copy(entries = self.entries + (mkobj(entry),))

@dataclass(frozen=True)
class yaexpand(yatype):
    ''' Helper virtual type to construct mappings. One of these gets
        pushed onto the stack for each key-value pair of a mapping and
        will return its type called with key and first child when being
        resolved. '''

    key: str
    value_schema: yamatchable
    type: PairlikeCallable = pair

    def matches(self, node: YAMLNode) -> yatype:
        return self.value_schema.matches(node)

    def match_children(self, node: YAMLNode) -> MatchedChildren:
        yield (node, self.value_schema.matches(node))

    def resolve(self, value: List[Any]) -> Any:
        return self.type(self.key, value[0])

    def construct_leaf(self, constructor: SafeConstructor,
                             node: YAMLNode) -> Any:
        raise NotImplementedError()


@dataclass(frozen=True, init=True)
class yanode_data:
    ''' Helper class to make mypy happy with the abstract class yanode. '''
    tag: RegexPattern
    type: Optional[Callable] = None # pylint: disable=E1136

class yanode(yanode_data,yatype):
    ''' Abstract class that represents one node of the YAML parse tree.
        Implements a generic matching algorith using the nodes YAML tag. '''

    def __init__(self, tag: OptField[str] = MISSING,
                       type: OptField[Optional[Callable]] = MISSING) -> None:
        with unfreeze(self) as unfrozen:
            if tag is not MISSING:
                unfrozen.tag = re_compile(tag)
            if type is not MISSING:
                unfrozen.type = type

        if not hasattr(self, 'tag'):
            raise SchemaError(
                'Field \'tag\' neither defined as class attribute nor ' +
                'constructor argument'
            )

    def matches(self, node: YAMLNode) -> yatype:
        if self.tag.fullmatch(node.tag):
            return self

        raise NoMatchingType(node)

    def resolve(self, value: Any) -> Any:
        return value if self.type is None else self.type(value)

class yaleafnode(yanode):
    ''' Helper for representing leaf nodes. Implements match_children as
        always returing None. '''
    def match_children(self, node: YAMLNode) -> None:
        return None

class yabranchnode(yanode):
    ''' Helper for representing branch nodes. Implements construct_leaf
        by raising an Exception. '''
    def construct_leaf(self, constructor: SafeConstructor,
                             node: YAMLNode) -> Any:
        raise TypeError(
            'Branch node cannot be constructed as leaf. This is most ' +
            'probably caused by an erroneous implementation of ' +
            'match_children.'
        )


@dataclass(frozen=True, init=False)
class yascalar(yaleafnode):
    ''' Helper class representing all kinds of YAML scalar nodes. Can be
        used as a catch-all. '''

    tag: RegexPattern = re_compile(
        r'tag:yaml\.org,2002:(str|int|float|null|bool)'
    )
    value: Optional[RegexPattern] = None
    construct: ConstructCallable = staticmethod(as_scalar) # type: ignore

    def __init__(self, tag: OptField[str] = MISSING,
                       type: OptField[Callable] = MISSING,
                       value: OptField[str] = MISSING,
                       construct: OptField[ConstructCallable] = MISSING) -> None:
        super().__init__(tag, type)
        with unfreeze(self) as unfrozen:
            if value is not MISSING:
                unfrozen.value = re_compile(value)
            if construct is not MISSING:
                unfrozen.construct = construct

    def matches(self, node: YAMLNode) -> yatype:
        super().matches(node)
        if not self.value or self.value.fullmatch(node.value):
            return self

        raise NoMatchingType(node)

    def construct_leaf(self, constructor: SafeConstructor,
                             node: YAMLNode) -> Any:
        return self.construct(constructor, node) # type: ignore

@dataclass(frozen=True, init=False)
class yastr(yascalar):
    ''' More specific scalar type to only match string. '''
    tag: RegexPattern = re_compile(r'tag:yaml\.org,2002:str')

@dataclass(frozen=True, init=False)
class yanull(yascalar):
    ''' More specific scalar type to only match the YAML null value. '''
    tag: RegexPattern = re_compile(r'tag:yaml\.org,2002:null')

@dataclass(frozen=True, init=False)
class yabool(yascalar):
    ''' More specific scalar type to only match the YAML booleans. '''
    tag: RegexPattern = re_compile(r'tag:yaml\.org,2002:bool')

@dataclass(frozen=True, init=False)
class yanumber(yascalar):
    ''' More specific scalar type to only match the YAML numbers. '''
    tag: RegexPattern = re_compile(r'tag:yaml\.org,2002:(int|float)')

@dataclass(frozen=True, init=False)
class yaint(yanumber):
    ''' More specific scalar type to only match the YAML ints. '''
    tag: RegexPattern = re_compile(r'tag:yaml\.org,2002:int')

@dataclass(frozen=True, init=False)
class yafloat(yanumber):
    ''' More specific scalar type to only match the YAML floats. '''
    tag: RegexPattern = re_compile(r'tag:yaml\.org,2002:float')


@dataclass(frozen=True)
class yaentry(yacopyable):
    ''' Possible schema type of an mapping entry. Supports various
        options to configure how and what key-value pairs are matched. '''

    required: bool = False
    repeat: bool = False
    keys: Tuple[Tuple[RegexPattern, yamatchable, PairlikeCallable], ...] = \
        field(init=False, default=())

    def match_item(self, key: str, value: YAMLNode) -> EntryMatchResult:
        ''' Tries to match this entry type to the given key-node pair.
            This is the mapping analog to the yamatchable.match method. '''

        for (regex, schema, type) in self.keys:
            if not regex.fullmatch(key):
                continue

            with suppress(NoMatchingType):
                return (key, schema.matches(value), type)

        return None

    def case(self, pattern: str, schema: MatchArgument,
                   type: PairlikeCallable = pair) -> yaentry:
        ''' Add a possible key-type pair to the alternatives matched by
            this entry. '''
        return self.copy(
            keys = self.keys + ((re_compile(pattern), mkobj(schema), type),)
        )

    @property
    def keys_repr(self) -> str:
        ''' Helper method to get more readable exception messages from
            yamap.match_children. '''
        return '({})'.format(' | '.join(r.pattern for r,s,t in self.keys))

@dataclass(frozen=True, init=False)
class yamap(yabranchnode):
    ''' Represents a YAML mapping node. '''

    tag: RegexPattern = re_compile(r'tag:yaml\.org,2002:map')
    type: Optional[Callable[[Sequence[Tuple[Any, Any]]], Any]] = dict
    entries: Tuple[yaentry, ...] = ()

    def __init__(self, tag: OptField[str] = MISSING,
                       type: OptField[Optional[Callable]] = MISSING,
                       squash: bool = False,
                       unpack: bool = False) -> None:
        if isinstance(type, _MISSING_TYPE):
            type = self.type
        if squash and unpack:
            raise SchemaError('squash and unpack cannot be used at the same time')
        if type is None:
            if squash or unpack:
                raise SchemaError('squash and unpack require a type')
        else:
            if squash:
                type = squashed(type)
            elif unpack:
                type = unpacked_map(type)
        super().__init__(tag, type)

    def match_children(self, node: YAMLNode) -> MatchedChildren:
        counts: Dict[yaentry, int] = defaultdict(lambda: 0)

        for key_node,value in reversed(node.value):
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
            yield (value, yaexpand(*match))

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

    def entry(self, entry: yaentry) -> yamap:
        ''' Add a yaentry to this mapping. '''
        return self.copy(entries = self.entries + (entry,))

    def case(self, regex: str, schema: MatchArgument,
                   type: PairlikeCallable = pair,
                   repeat: bool = False, required: bool = False) -> yamap:
        ''' Shortcut to add a yaentry to this mapping without having
            to go through object creation. '''
        return self.entry(
            yaentry(required=required, repeat=repeat).case(regex, schema, type)
        )

    def zero_or_one(self, regex: str, schema: MatchArgument,
                          type: PairlikeCallable = pair) -> yamap:
        ''' Shortcut to add an optional yaentry to this mapping. '''
        return self.case(regex, schema, type)

    def exactly_one(self, regex: str, schema: MatchArgument,
                          type: PairlikeCallable = pair) -> yamap:
        ''' Shortcut to add a required yaentry to this mapping. '''
        return self.case(regex, schema, type, required=True)

    def zero_or_more(self, regex: str, schema: MatchArgument,
                           type: PairlikeCallable = pair) -> yamap:
        ''' Shortcut to add an optional and repeatable yaentry to this
            mapping. '''
        return self.case(regex, schema, type, repeat=True)

    def one_or_more(self, regex: str, schema: MatchArgument,
                          type: PairlikeCallable = pair) -> yamap:
        ''' Shortcut to add a required and repeatable yaentry to this
             mapping. '''
        return self.case(regex, schema, type, repeat=True, required=True)


@dataclass(frozen=True, init=False)
class yaseq(yabranchnode):
    ''' Represents a YAML sequence node. '''

    tag: RegexPattern = re_compile(r'tag:yaml\.org,2002:seq')
    type: Optional[Callable[[Sequence[Any]], Any]] = list
    schema: yaoneof = yaoneof()

    def __init__(self, tag: OptField[str] = MISSING,
                       type: OptField[Optional[Callable]] = MISSING,
                       unpack: bool = False) -> None:
        if isinstance(type, _MISSING_TYPE):
            type = self.type
        if type is None:
            if unpack:
                raise SchemaError('unpack requires a type')
        else:
            if unpack:
                type = unpacked_seq(type)
        super().__init__(tag, type)

    def match_children(self, node: YAMLNode) -> MatchedChildren:
        for item in reversed(node.value):
            yield (item, self.schema.matches(item))

    def case(self, schema: MatchArgument) -> yaseq:
        ''' Register an additonal schema type option. '''
        return self.copy(schema = self.schema.case(schema))


__all__ = (
    'yaoneof',
    'yascalar',
    'yastr',
    'yanull',
    'yabool',
    'yanumber',
    'yaint',
    'yafloat',
    'yaentry',
    'yamap',
    'yaseq',
)
