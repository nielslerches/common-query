import operator

from functools import reduce
from itertools import groupby, tee, islice


def nwise(xs, n=2):
    return zip(*(islice(xs, idx, None) for idx, xs in enumerate(tee(xs, n))))


class LazyObject:
    pass


class Comparable(LazyObject):
    def __eq__(self, other):
        return Eq(self, other)

    def __ne__(self, other):
        return Ne(self, other)

    def __gt__(self, other):
        return Gt(self, other)

    def __ge__(self, other):
        return Ge(self, other)

    def __lt__(self, other):
        return Lt(self, other)

    def __le__(self, other):
        return Le(self, other)

    def __and__(self, other):
        return And(self, other)

    def __or__(self, other):
        return Or(self, other)


class ArithmeticOperable(LazyObject):
    def __add__(self, other):
        return Add(self, other)

    def __radd__(self, other):
        return Add(other, self)

    def __sub__(self, other):
        return Sub(self, other)

    def __rsub__(self, other):
        return Sub(other, self)

    def __mul__(self, other):
        return Mul(self, other)

    def __rmul__(self, other):
        return Mul(other, self)

    def __truediv__(self, other):
        return TrueDiv(self, other)

    def __rtruediv__(self, other):
        return TrueDiv(other, self)

    def __floordiv__(self, other):
        return FloorDiv(self, other)

    def __rfloordiv__(self, other):
        return FloorDiv(other, self)

    def __neg__(self):
        return Neg(self)


class UnaryOperation(Comparable, ArithmeticOperable):
    def __init__(self, operand):
        self.operand = operand

    def __repr__(self):
        return '{}({!r})'.format(self.op, self.operand)


class BinaryOperation(Comparable, ArithmeticOperable):
    __slots__ = ('operands',)

    op = '?'
    reducer = None
    precalc = False

    def __init__(self, *_operands):
        operands = []
        for operand in _operands:
            if type(operand) == type(self):
                operands.extend(operand.operands)
            else:
                operands.append(operand)

        if self.precalc and self.reducer:
            groups = [list(group) for _, group in groupby(operands, lambda obj: hash(type(obj)))]
            operands = [reduce(self.reducer, group) for group in groups]

        self.operands = operands

    def __getattr__(self, name):
        if name in dir(type(self)):
            return super(A, self).__getattr__(name)

        return GetAttr(name, self)

    def __call__(self, *args, **kwargs):
        return Call((args, kwargs), self)

    def __getitem__(self, key):
        return GetItem(key, self)

    def __invert__(self):
        if type(self) == Eq:
            return Ne(*self.operands)
        elif type(self) == Ne:
            return Eq(*self.operands)
        elif type(self) == Gt:
            return Le(*self.operands)
        elif type(self) == Ge:
            return Lt(*self.operands)
        elif type(self) == Lt:
            return Ge(*self.operands)
        elif type(self) == Le:
            return Gt(*self.operands)

        return Not(self)

    def __repr__(self):
        return ' {} '.format(self.op).join(repr(operand) for operand in self.operands)


class BooleanOperation:
    pass


class ArithmeticOperation:
    pass


class Eq(BooleanOperation, BinaryOperation):
    op = '=='
    reducer = operator.eq


class Ne(BooleanOperation, BinaryOperation):
    op = '!='
    reducer = operator.ne


class Gt(BooleanOperation, BinaryOperation):
    op = '>'
    reducer = operator.gt


class Ge(BooleanOperation, BinaryOperation):
    op = '>='
    reducer = operator.ge


class Lt(BooleanOperation, BinaryOperation):
    op = '<'
    reducer = operator.lt


class Le(BooleanOperation, BinaryOperation):
    op = '>='
    reducer = operator.le


class And(BooleanOperation, BinaryOperation):
    op = '&'
    reducer = operator.and_


class Or(BooleanOperation, BinaryOperation):
    op = '|'
    reducer = operator.or_


class Not(BooleanOperation, UnaryOperation):
    op = '~'
    reducer = operator.invert

    def __invert__(self):
        return self.operand


class Add(ArithmeticOperation, BinaryOperation):
    op = '+'
    reducer = operator.add
    precalc = True


class Sub(ArithmeticOperation, BinaryOperation):
    op = '-'
    reducer = operator.sub


class Mul(ArithmeticOperation, BinaryOperation):
    op = '*'
    reducer = operator.mul
    precalc = True


class TrueDiv(ArithmeticOperation, BinaryOperation):
    op = '/'
    reducer = operator.truediv


class FloorDiv(ArithmeticOperation, BinaryOperation):
    op = '//'
    reducer = operator.floordiv


class Neg(ArithmeticOperation, UnaryOperation):
    op = '-'
    reducer = operator.neg

    def __neg__(self):
        return self.operand


class A(Comparable, ArithmeticOperable):
    __slots__ = ('arguments', 'parent')

    def __init__(self, arguments, parent=None):
        self.arguments = arguments
        self.parent = parent

    def __getattr__(self, name):
        if name in dir(type(self)):
            return super(A, self).__getattr__(name)

        return GetAttr(name, self)

    def __call__(self, *args, **kwargs):
        return Call((args, kwargs), self)

    def __getitem__(self, key):
        return GetItem(key, self)

    def __repr__(self):
        return 'A({!r})'.format(self.arguments)


class GetAttr(A):
    def __repr__(self):
        return '{!r}.{}'.format(self.parent, self.arguments)


class Call(A):
    def __repr__(self):
        args, kwargs = self.arguments
        arguments = [repr(arg) for arg in args] + ['{}={!r}'.format(kw, repr(arg)) for kw, arg in kwargs.items()]
        arguments = ', '.join(arguments)
        return '{!r}({})'.format(self.parent, arguments)


class GetItem(A):
    def __repr__(self):
        return '{!r}[{}]'.format(self.parent, self.arguments)


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

    def dump(self):
        return self._entities

    def __repr__(self):
        return '<MemoryRepository [{}]>'.format(
            ', '.join(
                repr(entity)
                for entity
                in self._entities[0:3]
            ) + (', ...' if len(self._entities) > 3 else '')
        )
