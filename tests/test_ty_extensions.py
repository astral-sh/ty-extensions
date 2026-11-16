import importlib.util
import unittest
from collections import namedtuple
from typing import Any, NamedTuple, get_type_hints

import ty_extensions
from ty_extensions import (
    AlwaysFalsy,
    AlwaysTruthy,
    Bottom,
    Intersection,
    JustComplex,
    JustFloat,
    NamedTupleLike,
    Not,
    Top,
    static_assert,
)


class TyExtensionsTests(unittest.TestCase):
    def test_public_exports(self) -> None:
        self.assertEqual(
            {name for name in vars(ty_extensions) if not name.startswith("_")},
            set(ty_extensions.__all__),
            msg="Non-private attributes are listed in ty_extensions.__all__",
        )
        self.assertIsNone(
            importlib.util.find_spec("ty_extensions._internal"),
            msg="ty_extensions._internal should not be available",
        )

    def test_special_forms_can_be_evaluated_at_runtime(self) -> None:
        class A: ...

        class B: ...

        def annotated(
            intersection: Intersection[A, B],
            negation: Not[A],
            top: Top[list[Any]],
            bottom: Bottom[list[Any]],
            truthy: AlwaysTruthy,
            falsy: AlwaysFalsy,
        ) -> None:
            pass

        get_type_hints(annotated)

    def test_aliases(self) -> None:
        self.assertIs(JustFloat, float)
        self.assertIs(JustComplex, complex)

    def test_named_tuple_like_runtime_test(self) -> None:
        class Point(NamedTuple):
            x: int
            y: int

        Coordinate = namedtuple("Coordinate", ["x", "y"])

        self.assertTrue(isinstance(Point(1, 2), NamedTupleLike))
        self.assertTrue(isinstance(Coordinate(1, 2), NamedTupleLike))
        self.assertFalse(isinstance((1, 2), NamedTupleLike))

    def test_assertion(self) -> None:
        self.assertIsNone(static_assert(True))
        with self.assertRaisesRegex(AssertionError, "^message$"):
            static_assert(False, "message")
