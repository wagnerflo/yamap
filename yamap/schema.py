import abc
import collections
import copy
import re
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
    pair,
    unfreeze,
)


class yatype(abc.ABC):
    def copy(self, **kwargs):
        new = copy.copy(self)
        with unfreeze(new) as unfrozen:
            for field in get_dataclass_fields(new):
                if field.name not in kwargs:
                    continue
                unfrozen[field.name] = kwargs[field.name]
        return new

class yamatchable(abc.ABC):
    @abc.abstractmethod
    def matches(self, node, throw=True):
        pass

class yaresolvable(abc.ABC):
    @abc.abstractmethod
    def resolve(self, value):
        pass

@dataclass(frozen=True)
class yatreeish_data:
    is_branch: bool = field(default=True, init=False, repr=False)

class yatreeish(yatreeish_data,yaresolvable):
    @abc.abstractmethod
    def match_children(self, node):
        pass


@dataclass(frozen=True)
class yaoneof(yatype,yamatchable):
    types: typing.Tuple[yatype, ...] = field(init=False, default=())

    def __init__(self, *types):
        with unfreeze(self) as unfrozen:
            unfrozen.types = tuple(map(mkobj, types))

    def __iter__(self):
        return iter(self.types)

    def matches(self, node, throw=True):
        for type in self.types:
            res = type.matches(node, throw=False)
            if res is not None:
                return res

        if throw:
            raise MappingError()

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
class yanode(yatype,yaresolvable,yamatchable):
    tag: initvar[str] = None
    tags: typing.Tuple[str, ...] = ()
    type: typing.Optional[typing.Callable[..., typing.Any]] = None

    def __post_init__(self, tag):
        if not self.tags and tag is not None:
            self.tags = (tag,)

    def matches(self, node, throw=True):
        if node.tag in self.tags:
            return self

        if throw:
            raise MappingError()

    def load(self, stream):
        return load_and_map(stream, self)

    def resolve(self, value):
        return value if self.type is None else self.type(value)

@dataclass(frozen=True)
class yaleafnode_data:
    is_branch: bool = field(default=False, init=False, repr=False)

class yaleafnode(yaleafnode_data,yanode):
    @abc.abstractmethod
    def construct(self, constructor, node):
        pass

class yabranchnode(yanode,yatreeish):
    pass


@dataclass(frozen=True)
class yascalar(yaleafnode):
    tags: typing.Tuple[str, ...] = ('tag:yaml.org,2002:str',
                                    'tag:yaml.org,2002:int')

    def construct(self, constructor, node):
        return constructor.construct_scalar(node)

@dataclass(frozen=True)
class yastr(yascalar):
    tags: typing.Tuple[str, ...] = ('tag:yaml.org,2002:str',)


@dataclass(frozen=True)
class yamap_data:
    tags: typing.Tuple[str, ...] = ('tag:yaml.org,2002:map',)

class yamap(yamap_data,yabranchnode):
    pass

@dataclass(frozen=True)
class yadict(yamap):

    @dataclass(frozen=True)
    class typeitem:
        regex: str
        type: yatype
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

    type: typing.Callable[[typing.Any], typing.Any] = dict
    types: typing.Tuple[typeitem, ...] = field(init=False, default=())

    def match_children(self, node):
        result = []
        counts = collections.defaultdict(lambda: 0)

        for key,value in node.value:
            if key.tag != 'tag:yaml.org,2002:str':
                raise Exception()

            key = key.value
            type,value_type = zip_first(
                lambda type: type.matches(key, value),
                self.types
            )

            if type is None:
                raise Exception('no matching type')

            counts[type] += 1
            result.append((value, yaexpand(key, value_type)))

        for type in self.types:
            if type.required and not counts[type]:
                raise Exception('required missing')

        return result

    def copy(self, *args, **kwargs):
        return super().copy(
            types = self.types + (self.typeitem(*args, **kwargs),)
        )

    def optional(self, key, value):
        return self.copy(re.escape(key), value)

    def required(self, key, value):
        return self.copy(re.escape(key), value, required=True)

    def zero_or_more(self, regex, value):
        return self.copy(regex, value, repeat=True)

    def one_or_more(self, regex, value):
        return self.copy(regex, value, repeat=True, required=True)


@dataclass(frozen=True)
class yasquashedmap(yamap):
    type: typing.Callable[[str, typing.Any], typing.Any] = pair
    value_type: typing.Optional[yatype] = field(init=False, default=None)

    def match_children(self, node):
        (key,value), = node.value
        if key.tag != 'tag:yaml.org,2002:str':
            raise Exception()

        return [(
            value,
            yaexpand(
                key.value,
                self.value_type.matches(node),
                type = self.type
            )
        )]

    def contains(self, value):
        if self.value_type is not None:
            raise Exception()
        return self.copy(value_type = mkobj(value))

    def resolve(self, value):
        return value[0]


@dataclass(frozen=True)
class yalist(yabranchnode):
    tags: typing.Tuple[str, ...] = ('tag:yaml.org,2002:seq',)
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
    'yasquashedmap',
    'yaexpand',
    'yalist',
)
