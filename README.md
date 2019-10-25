# common-query
A Python library for creating queries and compiling them to different targets.

# Creating queries

```python
query = A('users')[0]['name'].startswith('John')
```

Behind the scenes the library generates a tree-structure that represents the query. The nodes more or less maps to the Python magic methods.
The above query is actually the following:

```python
Call(
  arguments=(('John',), {}),
  parent=GetAttr(
    arguments='startswith',
    parent=GetItem(
      arguments='name',
      parent=GetItem(
        arguments=0,
        parent=A(
          arguments='users',
          parent=None
        )
      )
    )
  )
)
```

# Compiling queries

```python
compiler = LambdaCompiler()
program = compiler.compile(A('x') > 10)
print(program({'x': 11})) # True
```

A compiler in this case is just an object that transforms a tree. The `LambdaCompiler` that comes with this library simply transforms the tree into a `lambda` function. This function takes in a context object, which the compiled query is executed on.

# Special things

This library has the concept of function creation and execution:

```python
compiler = LambdaCompiler()
function = Function('x', A('x') * 2)
program = compiler.compile(function)
compiled_function = program({})
print(compiled_function(10)) # 20
```

An obvious idea would be to implement a compiler/transpiler that transform a tree into a tree of SQLAlchemy filters, or Django Q objects.
