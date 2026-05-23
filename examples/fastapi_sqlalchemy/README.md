# FastAPI + SQLAlchemy example

```bash
uv add fastapi sqlalchemy paramora
uv run fastapi dev app.py
```

Try:

```bash
curl "http://127.0.0.1:8000/items?price__gte=10&sort=-created_at"
```
