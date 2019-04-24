import operator

from functools import reduce
from itertools import groupby


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


class UnaryOperation(LazyObject):
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


class Eq(BinaryOperation):
    op = '=='
    reducer = operator.eq


class Ne(BinaryOperation):
    op = '!='
    reducer = operator.ne


class Gt(BinaryOperation):
    op = '>'
    reducer = operator.gt


class Ge(BinaryOperation):
    op = '>='
    reducer = operator.ge


class Lt(BinaryOperation):
    op = '<'
    reducer = operator.lt


class Le(BinaryOperation):
    op = '>='
    reducer = operator.le


class And(BinaryOperation):
    op = '&'
    reducer = operator.and_


class Or(BinaryOperation):
    op = '|'
    reducer = operator.or_


class Not(UnaryOperation):
    op = '~'
    reducer = operator.invert

    def __invert__(self):
        return self.operand


class Add(BinaryOperation):
    op = '+'
    reducer = operator.add
    precalc = True


class Sub(BinaryOperation):
    op = '-'
    reducer = operator.sub


class Mul(BinaryOperation):
    op = '*'
    reducer = operator.mul
    precalc = True


class TrueDiv(BinaryOperation):
    op = '/'
    reducer = operator.truediv


class FloorDiv(BinaryOperation):
    op = '//'
    reducer = operator.floordiv


class Neg(UnaryOperation):
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
                if node.parent:
                    return lambda item: getattr(self.compile(node.parent)(item), node.arguments)
                return lambda item: getattr(item, node.arguments)

            elif isinstance(node, Call):
                args, kwargs = node.arguments
                if node.parent:
                    return lambda item: self.compile(node.parent)(item)(*args, **kwargs)
                return lambda item: item(*args, **kwargs)

            elif isinstance(node, GetItem):
                if node.parent:
                    return lambda item: self.compile(node.parent)(item)[node.arguments]

                return lambda item: item[node.arguments]

            return lambda item: self.get_value(item, node.arguments)

        elif isinstance(node, BinaryOperation):
            return lambda item: reduce(
                node.reducer,
                [
                    (self.compile(operand)(item) if isinstance(operand, LazyObject) else operand)
                    for operand
                    in node.operands
                ]
            )

        elif isinstance(node, UnaryOperation):
            if isinstance(node.operand, LazyObject):
                return lambda item: node.reducer(hash(self.compile(node.operand)(item)))

            return lambda _: node.reducer(hash(node.operand))

        else:
            return node
