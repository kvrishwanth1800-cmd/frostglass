# Pending manual wiring edits for M7

These edits must be applied from an unredacted checkout. They connect the isolated M7 modules to the live application. Do not apply partially: each route must retain the existing server-side permission check and tenant scoping.

## 1. `frostglass/main.py`

**Anchor:**
```python
from frostglass.admin.store import AdminStore
```

**Insert after it:**
```python
from frostglass.admin.dictionary_store import DictionaryStore
from frostglass.admin.routes_dictionaries import create_router as create_dictionary_router
from frostglass.admin.routes_suggestions import create_router as create_suggestion_router
from frostglass.admin.suggestions_engine import generate_suggestions
```

**Anchor:**
```python
admin_store = AdminStore(audit_store.connection)
```

**Insert after it:**
```python
dictionary_store = DictionaryStore(audit_store.connection)
```

**Anchor:**
```python
app.include_router(create_admin_router(audit_store, admin_store, policy_engine, dry_run))
```

**Insert after it:**
```python
app.include_router(create_dictionary_router(dictionary_store, admin_store))
app.include_router(create_suggestion_router(audit_store, admin_store, policy_engine))
```

## 2. `frostglass/gateway/pipeline.py`

**Anchor:**
```python
class ProviderRegistry:
```

**Required change:** inject `DictionaryStore` into the registry and append dictionary findings, generated with the list action and replacement, to deterministic detector findings before policy evaluation. Use only `DictionaryStore.match(tenant_id, text)`. Do not store a matched source value in audit data. This wiring is required for AC-M7-01 to prove terms mask on the next request.

## 3. `frostglass/admin/routes_admin.py`

**Anchor:**
```python
class DictionaryCreate(BaseModel):
```

**Required change:** replace the legacy dictionary model and `/dictionaries` handlers with the M7 router in `frostglass/admin/routes_dictionaries.py`. The new router must require `READ_DICTIONARIES` for reads and `WRITE_DICTIONARIES` for all mutations.

**Anchor:**
```python
@router.get("/suggestions")
```

**Required change:** replace the legacy suggestion handlers with the M7 router in `frostglass/admin/routes_suggestions.py`. Its Apply operation must execute the proposed policy/detector configuration change transactionally before resolving the suggestion. It must require `READ_SUGGESTIONS` or `WRITE_SUGGESTIONS` as appropriate.

## Security review required

`custom_recognizers.py` rejects invalid syntax, lookarounds, backreferences, nested quantifiers, quantified alternation, unbounded wildcard repetition, and unbounded ranges. It does **not** claim to prove arbitrary Python regexes safe. Security review must approve this conservative allowlist before any custom recognizer can be saved or enabled.
