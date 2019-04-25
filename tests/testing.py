import unittest

from common_query import A
from common_query.testing import LambdaCompiler


class LambdaCompilerTestCase(unittest.TestCase):
    def setUp(self):
        self.compile = LambdaCompiler().compile

    def test_A(self):
        self.assertEqual(self.compile(A('x'))({'x': 10}), 10)
        self.assertEqual(self.compile(A(A('x')))({'x': 'y', 'y': 10}), 10)

    def test_GetAttr(self):
        class Person:
            def __init__(self, name):
                self.name = name

        self.assertEqual(self.compile(A('person').name)({'person': Person(name='Johnny')}), 'Johnny')

    def test_Call(self):
        self.assertEqual(self.compile(A('name').startswith('Jane'))({'name': 'Jane Doe'}), True)
        self.assertEqual(self.compile(A('last_name').startswith(A('first_name')))({'first_name': 'John', 'last_name': 'Johnson'}), True)

    def test_GetItem(self):
        self.assertEqual(self.compile(A('users')[0])({'users': ['Jane']}), 'Jane')
        self.assertEqual(self.compile(A('users')[A('index')])({'users': ['Jane', 'John'], 'index': 1}), 'John')

    def test_BooleanOperation(self):
        self.assertEqual(self.compile(A('x') < 10 < A('y'))({'x': 5, 'y': 15}), True)

    def test_ArithmeticOperation(self):
        self.assertEqual(self.compile(A('x') + 5)({'x': 5}), 10)

    def test_UnaryOperation(self):
        self.assertEqual(self.compile(~A('x'))({'x': False}), True)
        self.assertEqual(self.compile(-A('x'))({'x': 10}), -10)
