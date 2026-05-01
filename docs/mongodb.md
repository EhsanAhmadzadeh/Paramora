# MongoDB backend

MongoDB is the first Paramora backend. Paramora emits a `MongoQuery` object:

```python
@dataclass(frozen=True, slots=True)
class MongoQuery:
    filter: dict[str, Any]
    sort: list[tuple[str, int]]
    limit: int
    offset: int
```

Use it with PyMongo-style collections:

```python
mongo = query.to_mongo()

docs = (
    collection
    .find(mongo.filter)
    .sort(mongo.sort)
    .skip(mongo.offset)
    .limit(mongo.limit)
)
```

## Operator emission

| Paramora operator | MongoDB output |
| --- | --- |
| `eq` | direct field value |
| `ne` | `$ne` |
| `gt` | `$gt` |
| `gte` | `$gte` |
| `lt` | `$lt` |
| `lte` | `$lte` |
| `in` | `$in` |
| `nin` | `$nin` |

Range filters on the same field are merged into one Mongo operator dictionary.

## Security boundary

Paramora does not allow raw MongoDB operators in query parameters. Public APIs
should expose Paramora operators such as `price__gte`, not raw syntax such as
`price[$gte]` or `price__$gte`.
