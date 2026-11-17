"""Runtime support for experimental type system features supported by ty."""

import sys as _sys
from collections.abc import Iterable as _Iterable
from typing import Any as _Any
from typing import ClassVar as _ClassVar
from typing import LiteralString as _LiteralString
from typing import Protocol as _Protocol
from typing import Self as _Self
from typing import _GenericAlias, _SpecialForm, _type_check
from typing import runtime_checkable as _runtime_checkable

__all__ = [
    "AlwaysFalsy",
    "AlwaysTruthy",
    "Bottom",
    "Intersection",
    "JustComplex",
    "JustFloat",
    "NamedTupleLike",
    "Not",
    "Top",
    "static_assert",
]


def static_assert(condition: object, msg: _LiteralString | None = None) -> None:
    """Make sure that a certain condition holds at type-check time.

    Example:

        static_assert(sys.version_info[:2] >= (3, 13), "Python 3.13 or higher is required")

    At runtime, this works like a normal assertion statement."""
    assert condition, msg


# Like typing_extensions, subclass typing._SpecialForm to customize the repr.
class _TySpecialForm(_SpecialForm, _root=True):
    def __repr__(self) -> str:
        return f"ty_extensions.{self.__name__}"


@_TySpecialForm
def Intersection(self: _TySpecialForm, parameters: object) -> _GenericAlias:
    """
    `Intersection[T1, T2, ..., Tn]`, also spelled as `T1 & T2 & ... & Tn`, represents an intersection
    type: the set of all objects that inhabit all of the types `T1`, `T2`, ..., `Tn`.

    For any two fully static types `T1` and `T2`, `Intersection[T1, T2]` is a subtype of both `T1` and
    `T2`. For any type `T3` that is a subtype of both `T1` and `T2`, `Intersection[T1, T2]` is a
    supertype of `T3`.

    In the following example, although neither `P` nor `Q` is a subtype of the other, an instance of `S`
    inhabits `Intersection[P, Q]` because `S` inherits from both `P` and `Q`:

    ```python
    class P: ...
    class Q: ...
    class S(P, Q): ...

    s: Intersection[P, Q] = S()
    ```

    In type expressions, ty supports and displays the experimental spelling `T1 & T2`.
    """
    if not isinstance(parameters, tuple):
        parameters = (parameters,)
    message = f"{self} arguments must be types."
    items = tuple(_type_check(item, message) for item in parameters)
    return _GenericAlias(self, items)


@_TySpecialForm
def Not(self: _TySpecialForm, parameters: object) -> _GenericAlias:
    """
    `Not[T]`, also spelled as `~T`, represents the set of all objects that do not inhabit the type `T`.

    In type expressions, ty supports and displays the experimental spelling `~T`.
    """
    item = _type_check(parameters, f"{self} accepts only a single type.")
    return _GenericAlias(self, (item,))


@_TySpecialForm
def Top(self: _TySpecialForm, parameters: object) -> _GenericAlias:
    """
    `Top[T]` represents the "top materialization" of `T`.

    For any type `T`, the top [materialization] of `T` is a type that is
    a supertype of all materializations of `T`.

    For a [fully static] type `T`, `Top[T]` is always exactly the same type
    as `T` itself. For example, the top materialization of `Sequence[int]`
    is simply `Sequence[int]`.

    For a [gradual type] `T` that contains [`Any`][Any] or `Unknown` inside
    it, however, `Top[T]` will not be equivalent to `T`. `Top[Sequence[Any]]`
    evaluates to `Sequence[object]`: since `Sequence` is covariant, no
    possible materialization of `Any` exists such that a fully static
    materialization of `Sequence[Any]` would not be a subtype of
    `Sequence[object]`.

    `Top[T]` cannot be simplified further for invariant gradual types.
    `Top[list[Any]]` cannot be simplified to any other type: because `list`
    is invariant, `list[object]` is not a supertype of `list[int]`. The
    top materialization of `list[Any]` is simply `Top[list[Any]]`: the
    infinite union of `list[T]` for every possible fully static type `T`.

    [materialization]: https://typing.python.org/en/latest/spec/concepts.html#materialization
    [fully static]: https://typing.python.org/en/latest/spec/concepts.html#fully-static-types
    [gradual type]: https://typing.python.org/en/latest/spec/concepts.html#gradual-types
    [Any]: https://typing.python.org/en/latest/spec/special-types.html#any
    """
    item = _type_check(parameters, f"{self} accepts only a single type.")
    return _GenericAlias(self, (item,))


@_TySpecialForm
def Bottom(self: _TySpecialForm, parameters: object) -> _GenericAlias:
    """
    `Bottom[T]` represents the "bottom materialization" of `T`.

    For any type `T`, the bottom [materialization] of `T` is a type that is
    a subtype of all materializations of `T`.

    For a [fully static] type `T`, `Bottom[T]` is always exactly the same type
    as `T` itself. For example, the bottom materialization of `Sequence[int]`
    is simply `Sequence[int]`.

    For a [gradual type] `T` that contains [`Any`][Any] or `Unknown` inside it,
    however, `Bottom[T]` will not be equivalent to `T`. `Bottom[Sequence[Any]]`
    evaluates to `Sequence[Never]`: since `Sequence` is covariant, no
    possible materialization of `Any` exists such that a fully static
    materialization of `Sequence[Any]` would not be a supertype of
    `Sequence[Never]`. (`Sequence[Never]` is not the same type as the
    uninhabited type `Never`: for example, it is inhabited by the empty tuple,
    `()`.)

    For many invariant gradual types `T`, `Bottom[T]` is equivalent to
    [`Never`][Never], although ty will not necessarily apply this simplification
    eagerly.

    [materialization]: https://typing.python.org/en/latest/spec/concepts.html#materialization
    [fully static]: https://typing.python.org/en/latest/spec/concepts.html#fully-static-types
    [gradual type]: https://typing.python.org/en/latest/spec/concepts.html#gradual-types
    [Never]: https://typing.python.org/en/latest/spec/special-types.html#never
    [Any]: https://typing.python.org/en/latest/spec/special-types.html#any
    """
    item = _type_check(parameters, f"{self} accepts only a single type.")
    return _GenericAlias(self, (item,))


AlwaysTruthy = _Any
"""
`AlwaysTruthy` represents the set of all objects that always evaluate to `True` in a boolean
context.

`AlwaysTruthy` is inhabited by singleton objects such as `True` and `...`, as well as truthy
literal strings, integers and bytestrings. It can also be inhabited by instances of classes
with `__bool__` methods returning `Literal[True]`.

In practice, most Python objects inhabit neither `AlwaysTruthy` nor `AlwaysFalsy`, since
their boolean evaluation may be uncertain or depend on runtime state. For example, although
an instance of *exactly* `object` is always truthy, a variable annotated as having type
`object` could also be an instance of an arbitrary subclass of `object` that is always falsy.
This means that the boolean evaluation of a variable inferred as `object` is uncertain, so
`object` is not a subtype of `AlwaysTruthy`.

At runtime, `AlwaysTruthy` is an alias for `typing.Any`.
"""

AlwaysFalsy = _Any
"""
`AlwaysFalsy` represents the set of all objects that always evaluate to `False` in a boolean
context.

`AlwaysFalsy` is inhabited by singleton objects such as `False` and `None`, as well as the
literals `""`, `b""` and `0`. It can also be inhabited by instances of classes with `__bool__`
methods returning `Literal[False]`.

In practice, however, most Python objects inhabit neither `AlwaysTruthy` nor `AlwaysFalsy`,
since their boolean evaluation may be uncertain or depend on runtime state.

At runtime, `AlwaysFalsy` is an alias for `typing.Any`.
"""

JustFloat = float
"""
`JustFloat` represents an instance of the class `float`. This can be used to circumvent
the [type-system special case][numeric] that lets `float` annotations accept values of
type `int` as well.

At runtime, `JustFloat` is an alias for the built-in `float` class.

[numeric]: https://typing.python.org/en/latest/spec/special-types.html#special-cases-for-float-and-complex
"""

JustComplex = complex
"""
`JustComplex` represents an instance of the class `complex`. This can be used to circumvent
the [type-system special case][numeric] that lets `complex` annotations accept values of
type `float` or `int` as well.

At runtime, `JustComplex` is an alias for the built-in `complex` class.

[numeric]: https://typing.python.org/en/latest/spec/special-types.html#special-cases-for-float-and-complex
"""


@_runtime_checkable
class NamedTupleLike(_Protocol):
    """
    A protocol describing an interface that should be satisfied by all named tuples
    created using `typing.NamedTuple` or `collections.namedtuple`.

    At runtime, `isinstance(value, NamedTupleLike)` checks for the required members.
    """

    _fields: _ClassVar[tuple[_Any, ...]]
    _field_defaults: _ClassVar[dict[str, _Any]]

    @classmethod
    def _make(cls, iterable: _Iterable[_Any]) -> _Self: ...

    def _asdict(self, /) -> dict[str, _Any]: ...

    def _replace(self, *args: _Any, **kwargs: _Any) -> _Self: ...

    if _sys.version_info >= (3, 13):

        def __replace__(self, *args: _Any, **kwargs: _Any) -> _Self: ...
