from functools import reduce

from common_query import (
    A,
    BinaryOperation,
    BooleanOperation,
    Call,
    GetAttr,
    GetItem,
    L,
    LazyObject,
    Neg,
    UnaryOperation,
)
from common_query.utils import nwise


class LambdaCompiler:
    __slots__ = ('get_value',)

    def __init__(self, get_value=None):
        self.get_value = get_value or (lambda item, key: item[key])

    def compile(self, node):
        if isinstance(node, A):
            if isinstance(node, GetAttr):
                return lambda item: getattr(
                    self.compile(node.parent)(item),
                    node.arguments if not isinstance(node.arguments, LazyObject) else self.compile(node.arguments)(item)
                )

            elif isinstance(node, Call):
                args, kwargs = node.arguments
                return lambda item: self.compile(node.parent)(item)(
                    *[(arg if not isinstance(arg, LazyObject) else self.compile(arg)(item)) for arg in args],
                    **{
                        kw: (arg if not isinstance(arg, LazyObject) else self.compile(arg)(item))
                        for kw, arg
                        in kwargs.items()
                    }
                )

            elif isinstance(node, GetItem):
                return lambda item: self.compile(node.parent)(item)[
                    node.arguments if not isinstance(node.arguments, LazyObject) else self.compile(node.arguments)(item)
                ]

            elif isinstance(node, L):
                return lambda item: node.value(item) if not isinstance(node.value, LazyObject) and callable(node.value) else node.value

            return lambda item: self.get_value(
                item,
                node.arguments if not isinstance(node.arguments, LazyObject) else self.compile(node.arguments)(item)
            )

        elif isinstance(node, BinaryOperation):
            if isinstance(node, BooleanOperation):
                return lambda item: all(
                    node.reducer(
                        (self.compile(a)(item) if isinstance(a, LazyObject) else a),
                        (self.compile(b)(item) if isinstance(b, LazyObject) else b)
                    )
                    for a, b
                    in nwise(node.operands)
                )

            return lambda item: reduce(
                node.reducer,
                [
                    (self.compile(operand)(item) if isinstance(operand, LazyObject) else operand)
                    for operand
                    in node.operands
                ]
            )

        elif isinstance(node, UnaryOperation):
            return lambda item: node.reducer(self.compile(node.operand)(item)) if isinstance(node.operand, LazyObject) else node.reducer(node.operand)

        else:
            return node


class MemoryRepository:
    __slots__ = ('_entities', '_compiler')

    def __init__(self, _entities=None, _compiler=None):
        self._entities = _entities or []
        self._compiler = _compiler or LambdaCompiler()

    def filter(self, query):
        callback = self._compiler.compile(query)
        return MemoryRepository(
            [
                entity
                for entity
                in self._entities
                if callback(entity)
            ],
            _compiler=self._compiler,
        )

    def order_by(self, *fields):
        entities = self._entities.copy()

        for field in reversed(fields):
            if isinstance(field, Neg):
                entities.sort(key=lambda entity: self._compiler.compile(field.operand)(entity), reverse=True)
            else:
                entities.sort(key=lambda entity: self._compiler.compile(field)(entity))

        return MemoryRepository(
            entities,
            _compiler=self._compiler
        )

    def __iter__(self):
        return iter(self._entities)

    def __repr__(self):
        return '<MemoryRepository [{}]>'.format(
            ', '.join(
                repr(entity)
                for entity
                in self._entities[0:3]
            ) + (', ...' if len(self._entities) > 3 else '')
        )
