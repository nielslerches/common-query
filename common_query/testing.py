from functools import reduce

from common_query import (
    The,
    BinaryOperation,
    BooleanOperation,
    Call,
    GetAttr,
    GetItem,
    L,
    LazyObject,
    Neg,
    UnaryOperation,
    For,
    Function,
    If,
    Assign,
)
from common_query.utils import nwise


def update(dict_a, dict_b):
    dict_a.update(dict_b)
    return dict_a


def shadow(*dicts):
    result = reduce(lambda dict_a, dict_b: update(dict_a.copy(), dict_b), dicts)
    return result


class LambdaCompiler:
    __slots__ = ("get_value",)

    def __init__(self, get_value=None):
        self.get_value = get_value or (lambda item, key: item[key])

    def compile(self, node):
        if isinstance(node, The):
            if isinstance(node, GetAttr):
                return lambda item: getattr(
                    self.compile(node.parent)(item),
                    node.arguments
                    if not isinstance(node.arguments, LazyObject)
                    else self.compile(node.arguments)(item),
                )

            elif isinstance(node, Call):
                args, kwargs = node.arguments
                return lambda item: self.compile(node.parent)(item)(
                    *[
                        (
                            arg
                            if not isinstance(arg, LazyObject)
                            else self.compile(arg)(item)
                        )
                        for arg in args
                    ],
                    **{
                        kw: (
                            arg
                            if not isinstance(arg, LazyObject)
                            else self.compile(arg)(item)
                        )
                        for kw, arg in kwargs.items()
                    }
                )

            elif isinstance(node, GetItem):
                return lambda item: self.compile(node.parent)(item)[
                    node.arguments
                    if not isinstance(node.arguments, LazyObject)
                    else self.compile(node.arguments)(item)
                ]

            elif isinstance(node, L):
                return lambda item: node.value

            return lambda item: self.get_value(
                item,
                node.arguments
                if not isinstance(node.arguments, LazyObject)
                else self.compile(node.arguments)(item),
            )

        elif isinstance(node, BinaryOperation):
            if isinstance(node, BooleanOperation):
                return lambda item: all(
                    node.reducer(
                        (self.compile(a)(item) if isinstance(a, LazyObject) else a),
                        (self.compile(b)(item) if isinstance(b, LazyObject) else b),
                    )
                    for a, b in nwise(node.operands)
                )

            return lambda item: reduce(
                node.reducer,
                [
                    (
                        self.compile(operand)(item)
                        if isinstance(operand, LazyObject)
                        else operand
                    )
                    for operand in node.operands
                ],
            )

        elif isinstance(node, UnaryOperation):
            return (
                lambda item: node.reducer(self.compile(node.operand)(item))
                if isinstance(node.operand, LazyObject)
                else node.reducer(node.operand)
            )

        elif isinstance(node, For):
            return lambda item: (
                (self.compile(node.function)(item) or (lambda inner: inner))(obj)
                for obj in self.compile(node.value)(item)
            )

        elif isinstance(node, Function):
            return lambda item: lambda obj: self.compile(node.body)(
                shadow(item, {node.variable_name: obj})
            )

        elif isinstance(node, If):
            return (
                lambda item: self.compile(node.then)(item)
                if self.compile(node.value)(item)
                else None
            )

        elif isinstance(node, Assign):
            return lambda item: update(
                item.copy(), {node.name: self.compile(node.value)(item)}
            )

        else:
            return lambda item: node


class MemoryRepository:
    __slots__ = ("_get_entities", "_compiler", "_pipeline")

    class MultipleObjectsReturned(Exception):
        message = "Multiple objects returned"

    class ObjectDoesNotExist(Exception):
        message = "Object does not exist"

    def __init__(self, _get_entities=None, _compiler=None, _pipeline=None):
        self._get_entities = _get_entities or (lambda: [])
        self._compiler = _compiler or LambdaCompiler()
        self._pipeline = _pipeline or []

    def all(self):
        return self

    def filter(self, query):
        callback = self._compiler.compile(query)

        def _filter(entities):
            return [entity for entity in entities if callback(entity)]

        return MemoryRepository(
            _get_entities=self._get_entities,
            _compiler=self._compiler,
            _pipeline=self._pipeline + [_filter],
        )

    def order_by(self, *fields):
        def _order_by(entities):
            entities = entities.copy()
            for field in reversed(fields):
                if isinstance(field, Neg):
                    entities.sort(
                        key=lambda entity: self._compiler.compile(field.operand)(
                            entity
                        ),
                        reverse=True,
                    )
                else:
                    entities.sort(
                        key=lambda entity: self._compiler.compile(field)(entity)
                    )
            return entities

        return MemoryRepository(
            _get_entities=self._get_entities,
            _compiler=self._compiler,
            _pipeline=self._pipeline + [_order_by],
        )

    def values(self, *args):
        def _values(entities):
            return [
                {arg: self._compiler.get_value(entity, arg) for arg in args}
                for entity in entities
            ]

        return MemoryRepository(
            _get_entities=self._get_entities,
            _compiler=self._compiler,
            _pipeline=self._pipeline + [_values],
        )

    def values_list(self, *args, **kwargs):
        flat = kwargs.setdefault("flat", False)
        if flat and len(args) > 1:
            raise Exception(
                "Can't return flat MemoryRepository when there are multiple fields specified."
            )
        transform = (
            (
                lambda entity: tuple(
                    self._compiler.get_value(entity, arg) for arg in args
                )
            )
            if not flat
            else (lambda entity: entity[args[0]])
        )

        def _values_list(entities):
            return [transform(entity) for entity in entities]

        return MemoryRepository(
            _get_entities=self._get_entities,
            _compiler=self._compiler,
            _pipeline=self._pipeline + [_values_list],
        )

    def get(self, query):
        entities = list(self.filter(query))
        if len(entities) > 1:
            raise self.MultipleObjectsReturned
        elif not entities:
            raise self.ObjectDoesNotExist
        return entities[0]

    def first(self):
        entities = list(self)
        return entities[0] if entities else None

    def last(self):
        entities = list(self)
        return entities[-1] if entities else None

    def __iter__(self):
        entities = self._get_entities()
        for pipe in self._pipeline:
            entities = pipe(entities)
        return iter(entities)

    def __repr__(self):
        entities = list(self)
        return "<MemoryRepository [{}]>".format(
            ", ".join(repr(entity) for entity in entities[0:3])
            + (", ..." if len(entities) > 3 else "")
        )

