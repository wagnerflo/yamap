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

''' Contains the core functionality of this library as well as a bunch
    of related helper classes. '''

from __future__ import annotations

import dataclasses
import typing

import ruamel.yaml.loader
import ruamel.yaml.nodes
import yamap.schema

@dataclasses.dataclass
class stackitem:
    ''' Internal helper class for better readability when working with
        items on the Mapper stack. '''

    node: ruamel.yaml.nodes.Node
    schema: yamap.schema.yatype
    parent: typing.Optional[stackitem]  # pylint: disable=unsubscriptable-object
    children: typing.List[typing.Any] = dataclasses.field(default_factory=list)
    branch_visited: bool = dataclasses.field(default=False, init=False)

class Loader(ruamel.yaml.loader.SafeLoader):
    # pylint: disable=abstract-method

    ''' Our very ons subclass of the ruamel SafeLoader. We have this to
        minimize other users of ruame.yaml inadvertently foisting
        constructors, representers or resolvers on us. '''

    yaml_constructors: typing.Dict[typing.Any, typing.Any] = {}
    yaml_multi_constructors: typing.Dict[typing.Any, typing.Any] = {}
    yaml_representers: typing.Dict[typing.Any, typing.Any] = {}
    yaml_multi_representers: typing.Dict[typing.Any, typing.Any] = {}
    yaml_path_resolvers: typing.Dict[typing.Any, typing.Any] = {}
    yaml_implicit_resolvers: typing.Dict[typing.Any, typing.Any] = {}

def load_and_map(stream: typing.Any, schema: 'yamap.schema.yamatchable') -> typing.Any:
    ''' Iterative stack based implementation of the mapper.

        Visits each none-branch node once and each branch node (that
        being sequence or mapping) twice: Once before and once after
        working through all its children.

        The first visit will try to map all children to schema types
        using the method appropriate to the current type and push all of
        them on the stack to be evaluated in the iterations directly
        following.

        The second visit will (or the only one for none-branching nodes)
        will evaluate the actual value of the node using the children
        prepared before as context. '''

    if not hasattr(stream, 'read') and hasattr(stream, 'open'):
        stream = stream.open('rb')

    loader = Loader(stream)
    node = loader.get_single_node()
    stack = [stackitem(node, schema.matches(node), None)]

    while stack:
        # peak at top of stack
        top = stack[-1]

        # first time visiting this node
        if not top.branch_visited:
            children = top.schema.match_children(top.node)

            # and it is a branching node
            if children is not None:
                # push stackitems of its children
                for child_node,child_schema in children:
                    stack.append(stackitem(child_node, child_schema, top))

                # mark node as visited
                top.branch_visited = True

                # and iterate
                continue

        # otherwise pop from stack
        stack.pop()

        # second time visiting a branching node
        if top.branch_visited:
            value = top.children

        # visiting a leaf node
        else:
            value = top.schema.matches(top.node).construct_leaf(
                loader, top.node
            )

        # convert type
        value = top.schema.resolve(value)

        if top.parent:
            top.parent.children.append(value)
        else:
            return value
