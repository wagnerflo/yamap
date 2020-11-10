yaml = '''
item1:
  a: A
  b: B
item2:
  c: C
  d: D
'''

from yamap import *
from dataclasses import dataclass

@dataclass
class entry:
    key: str
    val: 'Any'

schema = (
    yadict(type=list)
      .zero_or_more(
          'item\d',
          type = entry,
          schema = yadict().zero_or_more('.+', yastr)
      )
)

print(schema.load(yaml))
