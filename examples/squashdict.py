yaml = '''
- item1:
    a: A
    b: B
- item2:
    c: C
    d: D
'''

from yamap import *

schema = (
    yaseq()
        .case(
            yamap(squash=True)
                .exactly_one('item\d', yamap().zero_or_more('.+', yastr))
        )
)

print(schema.load(yaml))
