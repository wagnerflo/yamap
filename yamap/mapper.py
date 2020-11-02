import typing

from . import schema
from dataclasses import dataclass,field
from ruamel.yaml.loader import SafeLoader
from ruamel.yaml.nodes import Node

@dataclass
class result:
    node: Node
    type: 'schema.yatype'
    parent: 'result'
    visited: bool = False
    children: typing.List['result'] = field(default_factory=list)

class Mapper:
    def load(self, stream, type):
        if not hasattr(stream, 'read') and hasattr(stream, 'open'):
            steam = stream.open('rb')

        loader = SafeLoader(stream)
        node = loader.get_single_node()
        stack = [result(node, type.matches(node), None)]

        while stack:
            top = stack[-1]

            # first time visiting a branching node
            if top.type.is_branch and not top.visited:
                top.visited = True
                stack.extend(
                    result(node, type, top)
                    for node,type in reversed(top.type.match_children(top.node))
                )

            else:
                stack.pop()

                # second time visiting a branching node
                if top.type.is_branch:
                    value = top.children

                # visiting a leaf node
                else:
                    value = top.type.matches(top.node).construct(
                        loader, top.node
                    )

                # convert type
                value = top.type.resolve(value)

                if stack:
                    top.parent.children.append(value)
                else:
                    return value
