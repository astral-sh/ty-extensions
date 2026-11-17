import importlib.util
import inspect
import unittest
from typing import Any, get_args, get_origin, get_type_hints

import ty_extensions
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
        def annotated(
            intersection_empty: Intersection[()],
            intersection_single: Intersection[int],
            intersection: Intersection[int, bool],
            intersection_stringified: Intersection["int", "bool"],
            negation: Not[int],
            top: Top[list[Any]],
            bottom: Bottom[list[Any]],
            always_truthy: AlwaysTruthy,
            always_falsy: "AlwaysFalsy",
        ) -> None:
            pass

        hints = get_type_hints(annotated)

        with self.subTest("Intersection[()]"):
            self.assertIs(get_origin(hints["intersection_empty"]), Intersection)
            self.assertEqual(get_args(hints["intersection_empty"]), ())
            self.assertEqual(
                repr(hints["intersection_empty"]), "ty_extensions.Intersection[()]"
            )

        with self.subTest("Intersection[int]"):
            self.assertIs(get_origin(hints["intersection_single"]), Intersection)
            self.assertEqual(get_args(hints["intersection_single"]), (int,))
            self.assertEqual(
                repr(hints["intersection_single"]), "ty_extensions.Intersection[int]"
            )

        with self.subTest("Intersection[int, bool]"):
            self.assertIs(get_origin(hints["intersection"]), Intersection)
            self.assertEqual(get_args(hints["intersection"]), (int, bool))
            self.assertEqual(
                repr(hints["intersection"]),
                "ty_extensions.Intersection[int, bool]",
            )

        with self.subTest('Intersection["int", "bool"]'):
            self.assertIs(get_origin(hints["intersection_stringified"]), Intersection)
            self.assertEqual(get_args(hints["intersection_stringified"]), (int, bool))
            self.assertEqual(
                repr(hints["intersection_stringified"]),
                "ty_extensions.Intersection[int, bool]",
            )

        with self.subTest("Not[int]"):
            self.assertIs(get_origin(hints["negation"]), Not)
            self.assertEqual(get_args(hints["negation"]), (int,))
            self.assertEqual(repr(hints["negation"]), "ty_extensions.Not[int]")

        with self.subTest("Top[list[Any]]"):
            self.assertIs(get_origin(hints["top"]), Top)
            self.assertEqual(get_args(hints["top"]), (list[Any],))
            self.assertEqual(repr(hints["top"]), "ty_extensions.Top[list[typing.Any]]")

        with self.subTest("Bottom[list[Any]]"):
            self.assertIs(get_origin(hints["bottom"]), Bottom)
            self.assertEqual(get_args(hints["bottom"]), (list[Any],))
            self.assertEqual(
                repr(hints["bottom"]), "ty_extensions.Bottom[list[typing.Any]]"
            )

        with self.subTest("AlwaysTruthy"):
            self.assertIs(hints["always_truthy"], AlwaysTruthy)

        with self.subTest("AlwaysFalsy"):
            self.assertIs(hints["always_falsy"], AlwaysFalsy)

    def test_truthiness_special_forms(self) -> None:
        for name, special_form in (
            ("AlwaysTruthy", AlwaysTruthy),
            ("AlwaysFalsy", AlwaysFalsy),
        ):
            with self.subTest(name):
                self.assertEqual(repr(special_form), f"ty_extensions.{name}")
                self.assertIn(name, inspect.getdoc(special_form) or "")
                with self.assertRaisesRegex(
                    TypeError, rf"^ty_extensions\.{name} is not subscriptable$"
                ):
                    special_form[int]

    def test_truthiness_special_forms_as_type_arguments(self) -> None:
        self.assertEqual(
            get_args(Intersection[bool | None, AlwaysTruthy]),
            (bool | None, AlwaysTruthy),
        )
        self.assertEqual(get_args(int | AlwaysFalsy), (int, AlwaysFalsy))
        self.assertEqual(get_args(AlwaysFalsy | int), (AlwaysFalsy, int))

    def test_single_argument_special_forms_reject_multiple_arguments(self) -> None:
        for special_form in (Bottom, Not, Top):
            with (
                self.subTest(special_form=special_form),
                self.assertRaisesRegex(TypeError, "single type"),
            ):
                special_form[int, str]

    def test_aliases(self) -> None:
        self.assertIs(JustFloat, float)
        self.assertIs(JustComplex, complex)

    def test_assertion(self) -> None:
        self.assertIsNone(static_assert(True))
        with self.assertRaisesRegex(AssertionError, "^message$"):
            static_assert(False, "message")
