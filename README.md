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

```python
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
        callbacks = [self._compiler.compile(field) for field in fields]

        def sorting_key(entity):
            return tuple(callback(entity) for callback in callbacks)

        return MemoryRepository(
            list(
                sorted(
                    self._entities,
                    key=sorting_key
                )
            ),
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
```
