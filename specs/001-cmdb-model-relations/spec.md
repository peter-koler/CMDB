# Feature Specification: CMDB Model Relationships

**Feature Branch**: `001-cmdb-model-relations`  
**Created**: 2026-02-14  
**Status**: Draft  
**Input**: User description: "我已经做完了 cmdb 里面的模型和仓库，现在在做模型关系"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define Model Relationships (Priority: P1)

As a CMDB administrator, I want to define relationships between different model types so that I can represent how configuration items depend on or relate to each other.

**Why this priority**: Model relationships are fundamental to CMDB's core value - understanding the impact of changes and dependencies between infrastructure components.

**Independent Test**: Can create a relationship definition between two existing models (e.g., Server "hosts" Application) and verify it persists correctly.

**Acceptance Scenarios**:

1. **Given** two existing models (e.g., Server and Application), **When** I define a "hosts" relationship from Server to Application, **Then** the relationship type is stored and available for creating instance relationships
2. **Given** a model relationship definition, **When** I query the system, **Then** I can retrieve the relationship metadata including cardinality (1:1, 1:N, N:M)

---

### User Story 2 - Create Instance Relationships (Priority: P1)

As a CMDB user, I want to create actual relationships between configuration item instances so that I can track real infrastructure dependencies.

**Why this priority**: Without instance-level relationships, the CMDB cannot perform impact analysis or dependency mapping.

**Independent Test**: Can link two existing CI instances via a defined relationship type and query the relationship.

**Acceptance Scenarios**:

1. **Given** a Server instance "srv-001" and Application instance "app-001", **When** I create a "hosts" relationship between them, **Then** the relationship is persisted and retrievable
2. **Given** an existing instance relationship, **When** I query for related instances, **Then** I receive the correct linked CIs

---

### User Story 3 - Query Relationships (Priority: P2)

As a CMDB user, I want to query relationships in both directions (parent/child) so that I can perform impact analysis.

**Why this priority**: Impact analysis requires traversing relationships bidirectionally to find what affects what.

**Independent Test**: Can query "what servers host this application?" and "what applications run on this server?"

**Acceptance Scenarios**:

1. **Given** a relationship "Server A hosts Application B", **When** I query for Server A's children, **Then** I see Application B
2. **Given** the same relationship, **When** I query for Application B's parents, **Then** I see Server A

---

### User Story 4 - Validate Relationship Constraints (Priority: P2)

As a CMDB administrator, I want the system to enforce relationship cardinality constraints so that data integrity is maintained.

**Why this priority**: Prevents invalid data states (e.g., an application being hosted by multiple servers when only 1:1 is allowed).

**Independent Test**: System rejects relationship creation that violates defined cardinality rules.

**Acceptance Scenarios**:

1. **Given** a 1:1 relationship type between Server and Application, **When** I try to create a second relationship from another Server to the same Application, **Then** the system rejects with an appropriate error
2. **Given** a relationship type definition, **When** I create relationships within allowed cardinality, **Then** they are accepted

---

### Edge Cases

- What happens when a model is deleted that has existing relationships?
- How does system handle circular relationship dependencies?
- What happens when relationship type constraints change after relationships exist?
- How to handle relationship versioning and historical tracking?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support defining relationship types between any two models
- **FR-002**: Relationship types MUST specify cardinality (1:1, 1:N, N:M)  
- **FR-003**: Relationship types MUST have a name and optional description
- **FR-004**: System MUST support bidirectional naming (e.g., "hosts"/"runs on")
- **FR-005**: System MUST allow creating relationships between CI instances
- **FR-006**: System MUST enforce cardinality constraints at instance level
- **FR-007**: System MUST support querying relationships in both directions
- **FR-008**: System MUST prevent orphaned relationships when CIs are deleted
- **FR-009**: System MUST support cascading delete or restrict based on configuration
- **FR-010**: System MUST support relationship metadata (created_at, created_by, etc.)

### Key Entities

- **ModelRelationship**: Defines relationship types between models (source_model_id, target_model_id, name, reverse_name, cardinality)
- **InstanceRelationship**: Actual relationships between CI instances (source_ci_id, target_ci_id, model_relationship_id, metadata)
- **Cardinality**: Enum/constraints defining relationship multiplicity (ONE_TO_ONE, ONE_TO_MANY, MANY_TO_MANY)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Administrators can define a relationship type between any two models in under 1 minute
- **SC-002**: System enforces cardinality constraints with 100% accuracy
- **SC-003**: Querying relationships in either direction returns results in under 100ms for up to 10,000 relationships
- **SC-004**: No orphaned relationships exist after CI deletion (referential integrity maintained)
- **SC-005**: Users can traverse 3 levels of relationships in under 500ms

</content>