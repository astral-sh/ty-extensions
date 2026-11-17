"""Runtime support for experimental type system features supported by ty."""

import sys as _sys
from collections.abc import Iterable as _Iterable
from operator import getitem as _getitem
from types import FunctionType as _FunctionType
from typing import Any as _Any
from typing import ClassVar as _ClassVar
from typing import LiteralString as _LiteralString
from typing import Never as _Never
from typing import Protocol as _Protocol
from typing import Self as _Self
from typing import Union as _Union
from typing import _GenericAlias, _tp_cache, _type_check

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

    At runtime, a false condition raises AssertionError (even with Python optimization enabled)."""
    if not condition:
        raise AssertionError(msg)


# Evaluating Not[AlwaysTruthy] passes AlwaysTruthy to typing._type_check,
# which rejects instances of custom typing._SpecialForm subclasses. Use a
# standalone class, as typing_extensions does for its Self and Never backports.
class _TySpecialForm:
    __iter__ = None

    def __init__(self, getitem: _FunctionType) -> None:
        self.__name__ = getitem.__name__
        self.__qualname__ = getitem.__qualname__
        self.__doc__ = getitem.__doc__
        self._getitem = getitem

    def __init_subclass__(cls) -> _Never:
        raise TypeError("Cannot subclass ty-extensions special form classes")

    @_tp_cache
    def __getitem__(self, parameters: object) -> _GenericAlias:
        return self._getitem(self, parameters)

    def __repr__(self) -> str:
        return f"ty_extensions.{self.__name__}"

    def __reduce__(self) -> str:
        return self.__name__

    def __call__(self, *args: object, **kwargs: object) -> _Never:
        raise TypeError(f"Cannot instantiate {self!r}")

    def __mro_entries__(self, bases: tuple[object, ...]) -> _Never:
        raise TypeError(f"Cannot subclass {self!r}")

    def __instancecheck__(self, instance: object) -> _Never:
        raise TypeError(f"{self} cannot be used with isinstance()")

    def __subclasscheck__(self, subclass: type) -> _Never:
        raise TypeError(f"{self} cannot be used with issubclass()")

    def __or__(self, other: object) -> _Any:
        return _getitem(_Union, (self, other))

    def __ror__(self, other: object) -> _Any:
        return _getitem(_Union, (other, self))


class _IntersectionGenericAlias(_GenericAlias, _root=True):
    def __init__(
        self, origin: _TySpecialForm, args: _Iterable[object], **kwargs: _Any
    ) -> None:
        # Specialization and forward-reference resolution can introduce nested intersections
        # or duplicate operands. _GenericAlias.copy_with rebuilds the alias through this
        # constructor, so normalize the operands here.
        #
        # The flattening and deduplication logic is adapted from the helpers used by
        # typing.Literal in CPython.
        # https://github.com/python/cpython/blob/v3.15.1/Lib/typing.py#L366-L388
        flattened: list[object] = []
        for arg in args:
            if isinstance(arg, _IntersectionGenericAlias):
                flattened.extend(arg.__args__)
            else:
                flattened.append(arg)

        # Use the fast dictionary path for the common case of all hashable operands.
        # If any operand is unhashable, deduplicate the full list using slower equality
        # scans. For example, Annotated[int, []] is unhashable because its metadata
        # contains a list. Both paths keep the first occurrence of each operand.
        try:
            unique_args = tuple(dict.fromkeys(flattened))
        except TypeError:
            unique_items: list[object] = []
            for item in flattened:
                if item not in unique_items:
                    unique_items.append(item)
            unique_args = tuple(unique_items)

        super().__init__(origin, unique_args, **kwargs)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _IntersectionGenericAlias):
            return NotImplemented
        # Equal aliases can share a cached specialization. Compare __parameters__ in
        # order so each supplied argument binds to the same parameter on a cache hit.
        if self.__parameters__ != other.__parameters__:
            return False
        try:
            return set(self.__args__) == set(other.__args__)
        except TypeError:
            # Deduplication at construction makes equal lengths and membership
            # sufficient for order-insensitive comparison.
            return len(self.__args__) == len(other.__args__) and all(
                arg in other.__args__ for arg in self.__args__
            )

    def __hash__(self) -> int:
        return hash((frozenset(self.__args__), self.__parameters__))


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

    In type expressions, ty supports the experimental spelling `T1 & T2`, and also uses this syntax
    when displaying intersection types. While the experimental syntax will raise an exception in
    runtime contexts or in cases where an annotation expression could be evaluated, however,
    `Intersection[]` can be used in arbitrary contexts if the `ty-extensions` package is installed.

    Nested intersections are flattened at runtime, and duplicate operands are removed using
    runtime equality, keeping the first occurrence of each. A named alias created using the
    `type` statement is always kept as an operand. Intersections are unordered types, so
    nongeneric intersections always compare equal at runtime when they have the same
    operands:

    ```pycon
    >>> from ty_extensions import Intersection
    >>> Intersection[Intersection[str, int], str]
    ty_extensions.Intersection[str, int]
    >>> type Alias = Intersection[str, int]  # Python 3.12+
    >>> Intersection[Alias, str]
    ty_extensions.Intersection[Alias, str]
    >>> Intersection[int, str] == Intersection[str, int]
    True
    >>> hash(Intersection[int, str]) == hash(Intersection[str, int])
    True

    ```
    """
    if not isinstance(parameters, tuple):
        parameters = (parameters,)
    message = f"{self} arguments must be types."
    items = tuple(_type_check(item, message) for item in parameters)
    return _IntersectionGenericAlias(self, items)


@_TySpecialForm
def Not(self: _TySpecialForm, parameters: object) -> _GenericAlias:
    """
    `Not[T]`, also spelled as `~T`, represents the set of all objects that do not inhabit the type `T`.

    In type expressions, ty supports the experimental spelling `~T`, and also uses it when displaying
    negation types. While the experimental syntax will raise an exception in runtime contexts or in
    cases where an annotation expression could be evaluated, however, `Not[]` can be used in arbitrary
    contexts if the `ty-extensions` package is installed.
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


@_TySpecialForm
def AlwaysTruthy(self: _TySpecialForm, parameters: object) -> _Never:
    """
    `AlwaysTruthy` represents the set of all objects that always evaluate to `True` in a boolean
    context.

    `AlwaysTruthy` is inhabited by singleton objects such as `True` and `...`, as well as truthy
    literal strings, integers and bytestrings. It can also be inhabited by instances of classes
    with `__bool__` methods returning `Literal[True]`.

    In practice, most Python objects inhabit neither `AlwaysTruthy` nor `AlwaysFalsy`, since their
    boolean evaluation may be uncertain or depend on runtime state. For example, although an
    instance of *exactly* `object` is always truthy, a variable annotated as having type `object`
    could also be an instance of an arbitrary subclass of `object` that is always falsy. This means
    that the boolean evaluation of a variable inferred as `object` is uncertain, so `object` is
    not a subtype of `AlwaysTruthy`.
    """
    raise TypeError(f"{self} is not subscriptable")


@_TySpecialForm
def AlwaysFalsy(self: _TySpecialForm, parameters: object) -> _Never:
    """
    `AlwaysFalsy` represents the set of all objects that always evaluate to `False` in a boolean
    context.

    `AlwaysFalsy` is inhabited by singleton objects such as `False` and `None`, as well as the
    literals `""`, `b""` and `0`. It can also be inhabited by instances of classes with `__bool__`
    methods returning `Literal[False]`.

    In practice, however, most Python objects inhabit neither `AlwaysTruthy` nor `AlwaysFalsy`,
    since their boolean evaluation may be uncertain or depend on runtime state.
    """
    raise TypeError(f"{self} is not subscriptable")


JustFloat = float
"""
`JustFloat` represents an instance of the class `float`. This can be used to circumvent
the [type-system special case] that lets `float` annotations accept values of
type `int` as well.

At runtime, `JustFloat` is an alias for the built-in `float` class.

[type-system special case]: https://typing.python.org/en/latest/spec/special-types.html#special-cases-for-float-and-complex
"""

JustComplex = complex
"""
`JustComplex` represents an instance of the class `complex`. This can be used to circumvent
the [type-system special case] that lets `complex` annotations accept values of
type `float` or `int` as well.

At runtime, `JustComplex` is an alias for the built-in `complex` class.

[type-system special case]: https://typing.python.org/en/latest/spec/special-types.html#special-cases-for-float-and-complex
"""


class NamedTupleLike(_Protocol):
    """
    A protocol describing an interface that should be satisfied by all named tuples
    created using `typing.NamedTuple` or `collections.namedtuple`.
    """

    _fields: _ClassVar[tuple[_Any, ...]]
    _field_defaults: _ClassVar[dict[str, _Any]]

    @classmethod
    def _make(cls, iterable: _Iterable[_Any]) -> _Self: ...

    def _asdict(self, /) -> dict[str, _Any]: ...

    def _replace(self, *args: _Any, **kwargs: _Any) -> _Self: ...

    if _sys.version_info >= (3, 13):

        def __replace__(self, *args: _Any, **kwargs: _Any) -> _Self: ...
