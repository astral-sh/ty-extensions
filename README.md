# ty-extensions

[![PyPI](https://img.shields.io/pypi/v/ty-extensions.svg)](https://pypi.org/project/ty-extensions/)

This package makes [ty]'s experimental typing extensions importable at runtime. You can
add this package as a dependency to your project, if you want to use features from
`ty_extensions` and rely on runtime evaluation of these symbols.

```sh
uv add ty-extensions
```

You can then make use of features like [intersection types]:

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

[ty] checks these symbols using its [bundled `ty_extensions` stubs][stubs],
but the runtime will use the code defined in this package.

[intersection types]: https://docs.astral.sh/ty/features/type-system/#intersection-types
[ty]: https://docs.astral.sh/ty/
[stubs]: https://github.com/astral-sh/ruff/blob/main/crates/ty_vendored/ty_extensions/__init__.pyi
