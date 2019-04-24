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

# Example: creating a MemoryRepository

