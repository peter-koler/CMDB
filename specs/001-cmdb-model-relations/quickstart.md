# Quickstart: CMDB Model Relationships

**Feature**: CMDB Model Relationships  
**Goal**: Get developers up and running with the relationship feature in 5 minutes

## Prerequisites

- Python 3.11+
- Existing CMDB database with models and CI instances
- Backend dependencies installed: `pip install -r backend/requirements.txt`

## Setup

### 1. Database Migration

Run the database migration to add relationship tables:

```bash
cd backend
flask db migrate -m "add model relations"
flask db upgrade
```

### 2. Seed Default Relationship Types (Optional)

```bash
python scripts/seed_relation_types.py
```

This creates common relationship types like:
- `contains` / `belongs to`
- `hosts` / `runs on`  
- `depends on` / `required by`
- `connects to` / `connected from`

## Common Operations

### Define a New Relationship Type

**Scenario**: Define that "Server" hosts "Application"

```bash
curl -X POST http://localhost:5000/api/model-relation-types \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "hosts",
    "reverse_name": "runs on",
    "source_model_id": 1,
    "target_model_id": 2,
    "cardinality": "ONE_TO_MANY",
    "description": "Server hosts one or more applications"
  }'
```

### Create a CI Relationship

**Scenario**: Link Server "srv-001" to Application "app-001"

```bash
# Get the relation type ID first
RELATION_TYPE_ID=1

curl -X POST http://localhost:5000/api/ci-relations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "source_ci_id": 101,
    "target_ci_id": 201,
    "relation_type_id": '$RELATION_TYPE_ID'
  }'
```

### Query Relationships

**Get all relations for a CI** (both directions):

```bash
curl "http://localhost:5000/api/ci-instances/101/relations?direction=both" \
  -H "Authorization: Bearer <token>"
```

**Impact analysis** (find what depends on this CI):

```bash
curl "http://localhost:5000/api/ci-instances/101/related?depth=3" \
  -H "Authorization: Bearer <token>"
```

### Validate Before Creating

Check if a relationship is valid without creating it:

```bash
curl -X POST http://localhost:5000/api/ci-relations/validate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "source_ci_id": 101,
    "target_ci_id": 201,
    "relation_type_id": 1
  }'
```

## Testing

### Run Unit Tests

```bash
cd backend
pytest tests/unit/test_models/test_model_relation.py -v
```

### Run Integration Tests

```bash
pytest tests/integration/test_ci_relations_api.py -v
```

### Test Cardinality Constraints

```python
# Example: Test ONE_TO_MANY constraint
from app.models.model_relation import ModelRelationType, CiRelation

# Should succeed - first relation
relation1 = CiRelation(
    source_ci_id=101,
    target_ci_id=201, 
    relation_type_id=1  # ONE_TO_MANY
)
relation1.save()  # ✓ Success

# Should fail - second relation from same source
relation2 = CiRelation(
    source_ci_id=101,
    target_ci_id=202,
    relation_type_id=1  # ONE_TO_MANY
)
relation2.save()  # ✗ Fails - violates ONE_TO_MANY
```

## Development Guidelines

### Adding a New Relationship Type

1. Check if models exist: `GET /api/cmdb/models`
2. Create relation type: `POST /api/model-relation-types`
3. Verify in UI: Navigate to CMDB → Relations

### Handling Cascade Deletes

Configure cascade behavior when creating relation types:

- **`RESTRICT`** (default): Prevents CI deletion if relationships exist
- **`CASCADE`**: Automatically deletes relationships when CI is deleted
- **`SET_NULL`**: Sets relationship CI reference to NULL (not recommended for required relations)

Example for composition relationship:
```json
{
  "name": "contains",
  "reverse_name": "belongs to", 
  "source_model_id": 1,
  "target_model_id": 3,
  "cardinality": "ONE_TO_MANY",
  "on_delete": "CASCADE"
}
```

### Performance Tips

1. **Indexing**: Ensure indexes exist on `(source_ci_id, relation_type_id)` and `(target_ci_id, relation_type_id)`
2. **Query Optimization**: Use `direction` parameter to limit query scope
3. **Depth Limiting**: Keep impact analysis depth ≤ 3 for reasonable performance

## Troubleshooting

### "Cardinality constraint violated" Error

**Cause**: Attempting to create a relationship that exceeds the defined cardinality.

**Solution**: 
- Check existing relations: `GET /api/ci-instances/{id}/relations`
- Delete existing relation first, or choose a different relation type with MANY cardinality

### "Model mismatch" Error

**Cause**: Source/target CI models don't match the relation type definition.

**Solution**:
- Verify CI models: `GET /api/ci-instances/{id}`
- Check relation type: `GET /api/model-relation-types/{id}`
- Create appropriate relation type for these models

### Circular Reference Detection

**Cause**: Creating a relationship that would form a cycle (A→B→C→A).

**Solution**:
- Review impact tree: `GET /api/ci-instances/{id}/related?depth=5`
- Consider if cycle is intentional (e.g., network topology)
- Configure circular reference policy in relation type

## API Reference

See [contracts/openapi.yaml](./contracts/openapi.yaml) for complete API documentation.

## Next Steps

1. Read [data-model.md](./data-model.md) for entity details
2. Review [research.md](./research.md) for design decisions  
3. Check [spec.md](./spec.md) for requirements and acceptance criteria

## Support

- API Issues: Check `backend.log` for detailed error messages
- UI Issues: Verify frontend API calls in browser dev tools
- Database Issues: Run `flask db current` to verify migration status

</content>