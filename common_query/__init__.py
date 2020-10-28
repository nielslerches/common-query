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

    def __pow__(self, other):
        return Pow(self, other)

    def __rpow__(self, other):
        return Pow(other, self)

    def __mod__(self, other):
        return Mod(self, other)

    def __rmod__(self, other):
        return Mod(other, self)

    def __neg__(self):
        return Neg(self)


class UnaryOperation(Comparable):
    def __init__(self, operand):
        self.operand = operand

    def __repr__(self):
        return "{}({!r})".format(self.op, self.operand)


class Callable(LazyObject):
    def __call__(self, *args, **kwargs):
        return Call((args, kwargs), self)


class Accessible(Comparable, ArithmeticOperable, Callable):
    def __getattr__(self, name):
        if name in dir(type(self)):
            return super(Accessible, self).__getattr__(name)

        return GetAttr(name, self)

    def __getitem__(self, key):
        return GetItem(key, self)

    def __invert__(self):
        return Not(self)


class BinaryOperation(Accessible):
    __slots__ = ("operands",)

    op = "?"
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
            groups = [
                list(group)
                for _, group in groupby(operands, lambda obj: hash(type(obj)))
            ]
            operands = [reduce(self.reducer, group) for group in groups]

        self.operands = operands

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
        return " {} ".format(self.op).join(repr(operand) for operand in self.operands)


class BooleanOperation:
    pass


class ArithmeticOperation:
    pass


class Eq(BooleanOperation, BinaryOperation):
    op = "=="
    reducer = operator.eq


class Ne(BooleanOperation, BinaryOperation):
    op = "!="
    reducer = operator.ne


class Gt(BooleanOperation, BinaryOperation):
    op = ">"
    reducer = operator.gt


class Ge(BooleanOperation, BinaryOperation):
    op = ">="
    reducer = operator.ge


class Lt(BooleanOperation, BinaryOperation):
    op = "<"
    reducer = operator.lt


class Le(BooleanOperation, BinaryOperation):
    op = ">="
    reducer = operator.le


class And(BooleanOperation, BinaryOperation):
    op = "&"
    reducer = operator.and_


class Or(BooleanOperation, BinaryOperation):
    op = "|"
    reducer = operator.or_


class Not(BooleanOperation, UnaryOperation):
    op = "~"
    reducer = operator.not_

    def __invert__(self):
        return self.operand


class Add(ArithmeticOperation, BinaryOperation):
    op = "+"
    reducer = operator.add


class Sub(ArithmeticOperation, BinaryOperation):
    op = "-"
    reducer = operator.sub


class Mul(ArithmeticOperation, BinaryOperation):
    op = "*"
    reducer = operator.mul


class TrueDiv(ArithmeticOperation, BinaryOperation):
    op = "/"
    reducer = operator.truediv


class FloorDiv(ArithmeticOperation, BinaryOperation):
    op = "//"
    reducer = operator.floordiv


class Pow(ArithmeticOperation, BinaryOperation):
    op = "**"
    reducer = operator.pow


class Mod(ArithmeticOperation, BinaryOperation):
    op = "%"
    reducer = operator.mod


class Neg(ArithmeticOperation, ArithmeticOperable, UnaryOperation):
    op = "-"
    reducer = operator.neg

    def __neg__(self):
        return self.operand


class The(Accessible):
    __slots__ = ("arguments", "parent")

    def __init__(self, arguments, parent=None):
        self.arguments = arguments
        self.parent = parent

    def __repr__(self):
        return "The({!r})".format(self.arguments)


class GetAttr(The):
    def __repr__(self):
        return "{!r}.{}".format(self.parent, self.arguments)


class Call(The):
    def __repr__(self):
        args, kwargs = self.arguments
        arguments = [repr(arg) for arg in args] + [
            "{}={!r}".format(kw, repr(arg)) for kw, arg in kwargs.items()
        ]
        arguments = ", ".join(arguments)
        return "{!r}({})".format(self.parent, arguments)


class GetItem(The):
    def __repr__(self):
        return "{!r}[{}]".format(self.parent, self.arguments)


class Raw(The):
    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "Raw({!r})".format(self.value)


class For(LazyObject):
    def __init__(self, value, function=None):
        self.value = value
        self.function = function

    def do(self, function):
        return For(self.value, function=function)

    def __repr__(self):
        s = self.__class__.__name__ + "(" + repr(self.value) + ")"
        if self.function is not None:
            s += ".do(" + repr(self.function) + ")"
        return s


class Function(Callable):
    def __init__(self, variable_name, body):
        self.variable_name = variable_name
        self.body = body

    def __repr__(self):
        s = (
            self.__class__.__name__
            + "("
            + repr(self.variable_name)
            + ", "
            + repr(self.body)
            + ")"
        )
        return s


class If(LazyObject):
    def __init__(self, value, then, otherwise_then=None):
        self.value = value
        self.then = then
        self.otherwise_then = otherwise_then

    def otherwise(self, then):
        return If(self.value, self.then, otherwise_then=then,)

    def __repr__(self):
        s = (
            self.__class__.__name__
            + "("
            + repr(self.value)
            + ", "
            + repr(self.then)
            + ")"
        )
        if self.otherwise_then is not None:
            s += ".(" + repr(self.otherwise) + ")"
        return s


class Assign(LazyObject):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return (
            self.__class__.__name__
            + "("
            + repr(self.name)
            + ", "
            + repr(self.value)
            + ")"
        )

