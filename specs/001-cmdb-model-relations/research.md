# Research: CMDB Model Relationships

**Feature**: CMDB Model Relationships  
**Date**: 2026-02-14  
**Context**: Adding relationship management to existing CMDB system with models and CI instances already implemented

## Technical Decisions

### Decision: Extend Existing CiRelation vs Create New ModelRelationship Type

**Decision**: Create a two-tier relationship system:
1. `ModelRelationType` - Defines allowed relationship types between models (schema level)
2. Refactor `CiRelation` - Link CI instances using defined relationship types (instance level)

**Rationale**:
- Existing `CiRelation` only stores `relation_type` as a string without validation
- Need model-level definitions to enforce cardinality and valid model combinations
- Enables UI to show only valid relationship types when linking CIs
- Supports future features like relationship inheritance and constraints

**Alternatives considered**:
- **Keep simple string-based relations**: Rejected - no way to enforce valid model combinations or cardinality
- **Use single table with nullable fields**: Rejected - conflates schema definition with instance data
- **Graph database (Neo4j)**: Rejected - adds infrastructure complexity; SQL with proper indexing sufficient for expected scale

---

### Decision: Cardinality Implementation

**Decision**: Use Enum-based cardinality with database-level constraints + application validation

**Implementation**:
```python
class CardinalityType(Enum):
    ONE_TO_ONE = "1:1"      # One source -> One target
    ONE_TO_MANY = "1:N"     # One source -> Many targets  
    MANY_TO_ONE = "N:1"     # Many sources -> One target
    MANY_TO_MANY = "N:M"    # Many sources -> Many targets
```

**Rationale**:
- SQLAlchemy Enum provides type safety
- Application layer validates before database operations
- Unique constraints on database enforce 1:1 and N:1 relationships
- N:M relationships use standard join table pattern

**Alternatives considered**:
- **Check constraints only**: Rejected - harder to query and reason about
- **Separate tables per cardinality**: Rejected - excessive table proliferation
- **JSON column for flexible rules**: Rejected - loses type safety and queryability

---

### Decision: Cascade Behavior on CI Deletion

**Decision**: Support both CASCADE and RESTRICT with default RESTRICT, configurable per relationship type

**Implementation**:
- Add `on_delete` field to `ModelRelationType` (CASCADE/RESTRICT/SET_NULL)
- RESTRICT default prevents accidental data loss
- CASCADE for composition relationships (e.g., Server contains Disks)
- SET_NULL for optional relationships

**Rationale**:
- Referential integrity is critical for CMDB accuracy
- Different relationship semantics require different behaviors
- Users should explicitly choose destructive operations

**Alternatives considered**:
- **Always CASCADE**: Rejected - too dangerous for most relationships
- **Always RESTRICT**: Rejected - legitimate use cases for cascade (containment)
- **Soft delete with tombstones**: Rejected - adds complexity; can be added later if needed

---

### Decision: Relationship Directionality

**Decision**: Support bidirectional naming with source/target orientation

**Implementation**:
- `ModelRelationType` has `name` (source→target) and `reverse_name` (target→source)
- Example: "hosts"/"runs on", "contains"/"belongs to"
- Query API supports both directions via parameter

**Rationale**:
- Natural language matters for usability
- Impact analysis requires traversing both directions
- Single relationship record represents both perspectives

**Alternatives considered**:
- **Single name only**: Rejected - awkward to query "what runs on this server?" vs "what does this server host?"
- **Separate relation for each direction**: Rejected - data duplication and synchronization issues

---

### Decision: Database Indexing Strategy

**Decision**: Composite indexes on (source_ci_id, relation_type_id) and (target_ci_id, relation_type_id)

**Rationale**:
- Query patterns always filter by CI and optionally by relation type
- Bidirectional queries require indexing both sides
- Composite indexes cover most common query patterns

**Performance target**: < 100ms for queries up to 10,000 relationships (per spec SC-003)

---

### Decision: API Design Pattern

**Decision**: RESTful API with nested resource pattern

**Endpoints**:
- `/api/model-relation-types` - CRUD for relationship type definitions
- `/api/ci-instances/{id}/relations` - List/query relations for a CI
- `/api/ci-relations` - Create/delete instance relationships
- `/api/ci-instances/{id}/related?direction=both&type={type}` - Query related CIs

**Rationale**:
- Consistent with existing CMDB API patterns (observed in cmdb.py routes)
- Nested resources make relationship context clear
- Separate endpoints for schema (types) vs instance (relations) operations

**Alternatives considered**:
- **GraphQL**: Rejected - existing API uses REST; consistency preferred
- **Single /relations endpoint**: Rejected - unclear whether operating on types or instances

---

### Decision: Testing Strategy

**Decision**: 
- Unit tests for cardinality validation logic
- Integration tests for API endpoints with database
- Contract tests for relationship constraints

**Framework**: pytest (standard Python choice, no existing tests to conflict with)

**Coverage requirements**:
- All cardinality constraint scenarios
- Cascade behavior on deletion
- Bidirectional query correctness
- Edge cases (circular references, self-relations)

---

## Unknowns Resolved

1. **Technology Stack**: Python 3.x + Flask + SQLAlchemy (confirmed from existing codebase)
2. **Database**: SQLAlchemy-compatible (SQLite for dev, PostgreSQL for production)
3. **Existing Models**: `CmdbModel`, `CiInstance`, `CiRelation` exist with proper structure
4. **API Pattern**: RESTful with Flask blueprints (consistent with existing routes)

## Open Questions (Deferred to Implementation)

1. Should we support relationship attributes (e.g., "connected on port 8080")?
   - **Decision**: Phase 2 feature if needed

2. How to handle relationship versioning/history?
   - **Decision**: Can leverage existing `CiHistory` pattern if required

3. Self-referencing relationships (e.g., Server clusters with other Servers)?
   - **Decision**: Support via allowing source_model_id == target_model_id

</content>