import dataclasses
import ruamel.yaml.loader
import ruamel.yaml.nodes
import typing
import yamap.schema

@dataclasses.dataclass
class result:
    node: ruamel.yaml.nodes.Node
    type: 'yamap.schema.yatype'
    parent: 'result'
    visited: bool = False
    children: typing.List['result'] = dataclasses.field(default_factory=list)

class Mapper:
    def load(self, stream, type):
        if not hasattr(stream, 'read') and hasattr(stream, 'open'):
            stream = stream.open('rb')

        loader = ruamel.yaml.loader.SafeLoader(stream)
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
