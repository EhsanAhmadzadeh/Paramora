# FastAPI + Mongo ODM adapter example

```bash
uv add fastapi paramora
uv run fastapi dev app.py
```

Try:

```bash
curl "http://127.0.0.1:8000/items?status__in=free,busy&sort=-created_at"
```
