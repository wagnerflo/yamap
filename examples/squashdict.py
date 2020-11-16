yaml = '''
- item1:
    a: A
    b: B
- item2:
    c: C
    d: D
'''

from yamap import *
from dataclasses import dataclass
from typing import Any

@dataclass
class entry:
    key: str
    val: Any

schema = (
  yaseq()
    .case(
      yamap(type=entry, squash=True, unpack=True)
        .exactly_one('item\d', yamap().zero_or_more('.+', yastr))
    )
)

print(schema.load(yaml))
