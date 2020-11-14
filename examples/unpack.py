yaml = '''
- a: A1
  b: B1
- a: A2
'''

from yamap import *
from yamap.util import pair
from dataclasses import dataclass

@dataclass
class entry:
    a: str
    b: str = 'EMPTY'

schema = (
  yaseq(type=pair, unpack=True)
    .case(
      yamap(type=entry, unpack=True)
        .exactly_one('a', yastr)
        .zero_or_one('b', yastr)
    )
)

print(schema.load(yaml))
