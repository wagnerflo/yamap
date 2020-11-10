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
    yalist()
        .can_contain(
            yadict(squash=True)
                .required('item\d', yadict().zero_or_more('.+', yastr))
        )
)

print(schema.load(yaml))
