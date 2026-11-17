from collections.abc import Sequence
from typing import Any, Literal, Never, assert_type

from ty_extensions import (
    AlwaysFalsy,
    AlwaysTruthy,
    Bottom,
    Intersection,
    JustComplex,
    JustFloat,
    Not,
    Top,
    static_assert,
)


class A:
    a: int


class B:
    b: str


def intersection(value: Intersection[A, B]) -> None:
    assert_type(value.a, int)
    assert_type(value.b, str)


def negation(value: Intersection[int | str, Not[str]]) -> None:
    assert_type(value, int)


def materializations(top: Top[Sequence[Any]], bottom: Bottom[Sequence[Any]]) -> None:
    assert_type(top, Sequence[object])
    assert_type(bottom, Sequence[Never])


def truthiness(
    truthy: Intersection[bool | None, AlwaysTruthy],
    falsy: Intersection[bool | None, AlwaysFalsy],
) -> None:
    assert_type(truthy, Literal[True])
    assert_type(falsy, Literal[False] | None)


def exact_numeric_types() -> None:
    assert_type(1.0, JustFloat)
    assert_type(1j, JustComplex)


static_assert(1 + 2 == 3)
