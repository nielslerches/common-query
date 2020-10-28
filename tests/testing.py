import unittest

from common_query import The, L, Function, For
from common_query.testing import LambdaCompiler, MemoryRepository


class LambdaCompilerTestCase(unittest.TestCase):
    def setUp(self):
        self.compile = LambdaCompiler().compile

    def test_A(self):
        self.assertEqual(self.compile(The("x"))({"x": 10}), 10)
        self.assertEqual(self.compile(The(The("x")))({"x": "y", "y": 10}), 10)

    def test_GetAttr(self):
        class Person:
            def __init__(self, name):
                self.name = name

        self.assertEqual(
            self.compile(The("person").name)({"person": Person(name="Johnny")}),
            "Johnny",
        )

    def test_Call(self):
        self.assertEqual(
            self.compile(The("name").startswith("Jane"))({"name": "Jane Doe"}), True
        )
        self.assertEqual(
            self.compile(The("last_name").startswith(The("first_name")))(
                {"first_name": "John", "last_name": "Johnson"}
            ),
            True,
        )

    def test_GetItem(self):
        self.assertEqual(self.compile(The("users")[0])({"users": ["Jane"]}), "Jane")
        self.assertEqual(
            self.compile(The("users")[The("index")])(
                {"users": ["Jane", "John"], "index": 1}
            ),
            "John",
        )

    def test_L(self):
        self.assertEqual(self.compile(L("John"))({}), "John")
        self.assertEqual(self.compile(L(The("users")))({"users": 1}), The("users"))

    def test_BooleanOperation(self):
        self.assertEqual(
            self.compile((The("x") < 10) < The("y"))({"x": 5, "y": 15}), True
        )

    def test_ArithmeticOperation(self):
        self.assertEqual(self.compile(The("x") + 5)({"x": 5}), 10)

    def test_UnaryOperation(self):
        self.assertEqual(self.compile(~The("x"))({"x": False}), True)
        self.assertEqual(self.compile(-The("x"))({"x": 10}), -10)

    def test_Function(self):
        self.assertEqual(
            self.compile(Function("x", The("x") * 2))({})(3), 6,
        )
        self.assertEqual(
            self.compile(Function("x", The("x") * 2)(3))({}), 6,
        )

    def test_For(self):
        self.assertListEqual(
            list(self.compile(For(L([1, 2, 3])))({})), [1, 2, 3],
        )
        self.assertListEqual(
            list(self.compile(For(L([1, 2, 3])).do(Function("x", The("x") * 2)))({})),
            [2, 4, 6],
        )


class MemoryRepositoryTestCase(unittest.TestCase):
    def setUp(self):
        self.repository = MemoryRepository(
            _get_entities=lambda: [
                {"brand": "PUMA", "group": 4},
                {"brand": "Nike", "group": 4},
                {"brand": "adidas", "group": 3},
                {"brand": "Uhlsport", "group": 3},
                {"brand": "New Balance", "group": 3},
            ],
        )

    def test_filter(self):
        self.assertListEqual(
            ["Nike", "New Balance"],
            [
                d["brand"]
                for d in self.repository.filter(The("brand").lower().startswith("n"))
            ],
        )

    def test_order_by(self):
        self.assertListEqual(
            ["adidas", "New Balance", "Nike", "PUMA", "Uhlsport"],
            [d["brand"] for d in self.repository.order_by(The("brand").lower())],
        )
        self.assertListEqual(
            ["Nike", "PUMA", "adidas", "New Balance", "Uhlsport"],
            [
                d["brand"]
                for d in self.repository.order_by(-The("group"), The("brand").lower())
            ],
        )
