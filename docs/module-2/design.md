# Module 2 Design — Readiness Assessment

**Precondition:** Module 0 Definition of Done passes. A published `aph_version` with at least one rule exists (Module 1 done or fixture data loaded).

## Goal

Allow a College Admin to enter infrastructure data, then automatically compare it against the published APH rules to produce a gap report (met / partial / missing).

## New Migration: `0003_readiness_assessment.py`

Extends stub tables from Module 0. Never edits `0001_initial_schema.py`.

### `infrastructure_records`
Add columns to the stub:
- `institution_id UUID REFERENCES institutions(id)` — scoped to the college.
- `aph_version_id UUID REFERENCES aph_versions(id)` — which published version this entry is assessed against.
- `parameter_key TEXT` — normalized key matching `aph_rules.parameter_key`.
- `string_value TEXT` — used for non-numeric parameters.
- `numeric_value NUMERIC` — used for numeric parameters. Nullable.
- `unit TEXT`
- `evidence_note TEXT` — optional free-text description.
- `document_id UUID REFERENCES documents(id)` — optional supporting document.
- `recorded_by UUID REFERENCES users(id)`
- `recorded_at TIMESTAMPTZ DEFAULT NOW()`

Unique constraint: `(institution_id, aph_version_id, parameter_key)`.

### `readiness_snapshots` (new table)
- `id UUID PK`
- `institution_id UUID REFERENCES institutions(id)`
- `aph_version_id UUID REFERENCES aph_versions(id)`
- `generated_at TIMESTAMPTZ DEFAULT NOW()`
- `generated_by UUID REFERENCES users(id)`
- `summary JSONB` — `{total, met, partial, missing}` counts.
- `created_at`, `updated_at`

### `readiness_items` (new table)
- `id UUID PK`
- `snapshot_id UUID REFERENCES readiness_snapshots(id)`
- `rule_id UUID REFERENCES aph_rules(id)`
- `parameter_key TEXT`
- `status TEXT` — `met | partial | missing`
- `actual_numeric_value NUMERIC`
- `actual_string_value TEXT`
- `required_numeric_value NUMERIC`
- `required_string_value TEXT`
- `gap_description TEXT` — computed human-readable gap.
- `created_at`, `updated_at`

## Comparison Logic (`readiness_service.py`)

`compare(institution_id, aph_version_id) -> ReadinessSnapshot`:
1. Load all published rules for `aph_version_id`.
2. Load all `infrastructure_records` for `(institution_id, aph_version_id)`.
3. For each rule:
   - If no record for `parameter_key`: status = `missing`.
   - Numeric rule: compare `numeric_value` against rule `numeric_value` with `operator`. Full compliance = `met`; within 10 % = `partial`; below = `missing`.
   - String rule (`operator=in` or `=`): exact or set membership check. Match = `met`, else = `missing`.
4. Persist `readiness_snapshot` + `readiness_items`. Return snapshot id.

Rules are never modified by this service.

## API Endpoints (`/api/v1/readiness`)

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/records` | college_admin | Upsert one infrastructure record for own institution |
| GET | `/records` | college_admin | List own institution's records for a version |
| POST | `/snapshots` | college_admin | Run comparison, persist snapshot, return summary |
| GET | `/snapshots/{id}` | college_admin | Full gap report (all items) |
| GET | `/snapshots/{id}` | main_admin, regional_officer | Same endpoint; admin sees any institution, officer sees own region |

Institution scoping is enforced at service level, not just in routing.

## Gap Report Shape

```json
{
  "snapshot_id": "...",
  "generated_at": "...",
  "summary": { "total": 20, "met": 12, "partial": 3, "missing": 5 },
  "items": [
    {
      "parameter_key": "faculty_phd_count",
      "parameter": "Faculty with PhD",
      "status": "partial",
      "required": 5,
      "actual": 4,
      "unit": "count",
      "gap_description": "1 below minimum requirement"
    }
  ]
}
```

## Audit Events

`submit_infrastructure_record`, `generate_readiness_snapshot`.

## Out of Scope

- Bulk CSV import of infrastructure records.
- Automated re-comparison when a new APH version is published.
- Recommendations or AI-generated remediation text.
