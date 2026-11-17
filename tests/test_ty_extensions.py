import importlib.util
import inspect
import pickle
import unittest
from typing import Any, TypeVar, Union, get_args, get_origin, get_type_hints

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

_SPECIAL_FORMS = {
    "AlwaysFalsy": AlwaysFalsy,
    "AlwaysTruthy": AlwaysTruthy,
    "Bottom": Bottom,
    "Intersection": Intersection,
    "Not": Not,
    "Top": Top,
}
_SUBSCRIPTED_SPECIAL_FORMS = (
    Bottom[list[Any]],
    Intersection[int, bool],
    Not[int],
    Top[list[Any]],
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

    def test_bare_special_form_introspection(self) -> None:
        for name, special_form in _SPECIAL_FORMS.items():
            with self.subTest(name):
                self.assertEqual(special_form.__name__, name)
                self.assertEqual(special_form.__qualname__, name)
                self.assertEqual(repr(special_form), f"ty_extensions.{name}")
                self.assertIn(name, inspect.getdoc(special_form) or "")
                self.assertIsNone(get_origin(special_form))
                self.assertEqual(get_args(special_form), ())

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
            nested: list[Intersection["int", Not["str"]]],
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

        with self.subTest('list[Intersection["int", Not["str"]]]'):
            self.assertEqual(hints["nested"], list[Intersection[int, Not[str]]])

    def test_truthiness_special_forms_are_not_subscriptable(self) -> None:
        for name, special_form in (
            ("AlwaysTruthy", AlwaysTruthy),
            ("AlwaysFalsy", AlwaysFalsy),
        ):
            with (
                self.subTest(name),
                self.assertRaisesRegex(
                    TypeError, rf"^ty_extensions\.{name} is not subscriptable$"
                ),
            ):
                special_form[int]

    def test_truthiness_special_forms_as_type_arguments(self) -> None:
        self.assertEqual(
            get_args(Intersection[bool | None, AlwaysTruthy]),
            (bool | None, AlwaysTruthy),
        )
        self.assertEqual(get_args(Not[AlwaysTruthy]), (AlwaysTruthy,))
        self.assertIs(TypeVar("T", bound=AlwaysFalsy).__bound__, AlwaysFalsy)

    def test_special_forms_in_unions(self) -> None:
        for member in (AlwaysFalsy, AlwaysTruthy, *_SUBSCRIPTED_SPECIAL_FORMS):
            with self.subTest(member=member):
                form_first = member | int
                form_last = int | member
                self.assertIs(get_origin(form_first), Union)
                self.assertEqual(form_first, form_last)
                self.assertEqual(get_args(form_first), (member, int))
                self.assertEqual(get_args(form_last), (int, member))

    def test_none_as_a_special_form_argument(self) -> None:
        for special_form in (Bottom, Intersection, Not, Top):
            with self.subTest(special_form=special_form):
                self.assertEqual(get_args(special_form[None]), (type(None),))

    def test_single_argument_special_forms_reject_multiple_arguments(self) -> None:
        for special_form in (Bottom, Not, Top):
            with (
                self.subTest(special_form=special_form),
                self.assertRaisesRegex(TypeError, "single type"),
            ):
                special_form[int, str]

    def test_special_forms_with_type_variables(self) -> None:
        T = TypeVar("T")
        for generic, specialized in (
            (Bottom[list[T]], Bottom[list[int]]),
            (Intersection[T, bool], Intersection[int, bool]),
            (Not[T], Not[int]),
            (Top[list[T]], Top[list[int]]),
        ):
            with self.subTest(generic=generic):
                self.assertEqual(generic.__parameters__, (T,))
                self.assertEqual(generic[int], specialized)
                with self.assertRaises(TypeError):
                    specialized[str]

    def test_subscripted_special_form_equality_and_hashing(self) -> None:
        self.assertEqual(Intersection[int], Intersection[(int,)])
        self.assertEqual(hash(Intersection[int]), hash(Intersection[(int,)]))
        self.assertNotEqual(Intersection[int, bool], Intersection[int])
        self.assertNotEqual(Not[int], Not[str])
        self.assertNotEqual(Top[list[Any]], Bottom[list[Any]])

    def test_special_forms_cannot_be_used_as_classes(self) -> None:
        for special_form in (*_SPECIAL_FORMS.values(), *_SUBSCRIPTED_SPECIAL_FORMS):
            with self.subTest(special_form=special_form):
                with self.assertRaises(TypeError):
                    special_form()
                with self.assertRaises(TypeError):

                    class InvalidSubclass(special_form):
                        pass

                with self.assertRaises(TypeError):

                    class InvalidImplementationSubclass(type(special_form)):
                        pass

                with self.assertRaises(TypeError):
                    isinstance(1, special_form)
                with self.assertRaises(TypeError):
                    issubclass(int, special_form)

    def test_bare_special_form_pickle_round_trip(self) -> None:
        for special_form in _SPECIAL_FORMS.values():
            for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
                with self.subTest(special_form=special_form, protocol=protocol):
                    restored = pickle.loads(pickle.dumps(special_form, protocol))
                    self.assertIs(restored, special_form)

    def test_subscripted_special_form_pickle_round_trip(self) -> None:
        for special_form in (Intersection[()], *_SUBSCRIPTED_SPECIAL_FORMS):
            for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
                with self.subTest(special_form=special_form, protocol=protocol):
                    restored = pickle.loads(pickle.dumps(special_form, protocol))
                    self.assertEqual(restored, special_form)

    def test_aliases(self) -> None:
        self.assertIs(JustFloat, float)
        self.assertIs(JustComplex, complex)

    def test_assertion(self) -> None:
        self.assertIsNone(static_assert(True))
        with self.assertRaisesRegex(AssertionError, "^message$"):
            static_assert(False, "message")
