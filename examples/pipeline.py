yaml = '''
- upper
- replace: [FRIEND, MATE]
- replace: [HELLO, HEY]
'''

from yamap import *
from dataclasses import dataclass

def pipeline(items):
    input = 'Hello world, my friend!'
    for item in items:
        input = getattr(input, item.name)(*item.args)
    return input

@dataclass
class entry:
    name: str
    args: tuple = ()

schema = (
  yaseq(type=pipeline)
    .case(yastr(type=entry))
    .case(yamap(type=entry, squash=True, unpack=True)
            .exactly_one('.+', yaseq().case(yascalar)))
)

print(schema.load(yaml))
