from typing import assert_type

from ty_extensions import Intersection


class A:
    a: int


class B:
    b: str


def intersection(value: Intersection[A, B]) -> None:
    assert_type(value.a, int)
    assert_type(value.b, str)
