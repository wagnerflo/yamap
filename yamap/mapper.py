import dataclasses
import ruamel.yaml.loader
import ruamel.yaml.nodes
import typing
import yamap.schema

@dataclasses.dataclass
class stackitem:
    node: ruamel.yaml.nodes.Node
    schema: 'yamap.schema.yatype'
    parent: 'stackitem'
    visited: bool = False
    children: typing.List['stackitem'] = dataclasses.field(default_factory=list)

def load_and_map(stream, schema):
    if not hasattr(stream, 'read') and hasattr(stream, 'open'):
        stream = stream.open('rb')

    loader = ruamel.yaml.loader.StreamLoader(stream)
    node = loader.get_single_node()
    stack = [stackitem(node, schema.matches(node), None)]

    while stack:
        top = stack[-1]

        # first time visiting a branching node
        if top.schema.is_branch and not top.visited:
            top.visited = True
            stack.extend(
                stackitem(node, schema, top)
                for node,schema in reversed(top.schema.match_children(top.node))
            )

        else:
            stack.pop()

            # second time visiting a branching node
            if top.schema.is_branch:
                value = top.children

            # visiting a leaf node
            else:
                value = top.schema.matches(top.node).construct(
                    loader, top.node
                )

            # convert type
            value = top.schema.resolve(value)

            if stack:
                top.parent.children.append(value)
            else:
                return value
