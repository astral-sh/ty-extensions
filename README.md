# ty-extensions

This package makes ty's experimental typing extensions importable at runtime. You can
add this package as a dependency to your project, if you want to use features from
`ty_extensions` and rely on runtime evaluation of these symbols.

```sh
uv add ty-extensions
```

You can then make use of ty's experimental features like intersection types:

```python
import json
from typing import Protocol

from ty_extensions import Intersection


class Serializable(Protocol):
    def serialize_json(self) -> str: ...


class Versioned(Protocol):
    @property
    def version(self) -> int: ...


def output_as_json(obj: Intersection[Serializable, Versioned]) -> str:
    return json.dumps({
        "data": json.loads(obj.serialize_json()),
        "version": obj.version,
    })
```

[ty](https://docs.astral.sh/ty/) checks these symbols using its bundled `ty_extensions` stubs,
but the runtime will use the code defined in this package.
