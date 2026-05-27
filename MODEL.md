# MODEL.md

## Core shape

The app separates source capture from normalized audit rows.

- `Tenant`: company boundary. Every operational table is tenant-scoped.
- `Facility`: tenant-specific lookup for SAP plant codes and utility meter locations.
- `SourceConnector`: describes the source system, source type, ingestion mode, and config used to obtain data.
- `IngestionBatch`: one uploaded file or API pull. Stores filename, checksum, counts, status, and timestamps.
- `RawRecord`: immutable source row or segment payload with parse status and errors.
- `EmissionFactor`: versionable factor key, unit, scope, source note, and metadata.
- `ActivityRecord`: normalized review row used by analysts and auditors.
- `AuditEvent`: every analyst edit, approval, or rejection with before/after snapshots.

## Multi-tenancy

`Tenant` is a foreign key on facilities, connectors, batches, activity rows, and audit events. API requests default to `acme-industrials` for the demo but accept a `tenant` parameter. A production version would enforce tenant access through authenticated users and middleware; the data model is already shaped for that.

## Source of truth

The source of truth is never overwritten.

`RawRecord.payload` stores the exact parsed row or JSON segment. `ActivityRecord.raw_record` links normalized output back to the original input. `IngestionBatch.source_checksum` makes duplicate-file detection possible. Analyst edits are written to `ActivityRecord` while `AuditEvent.before` and `AuditEvent.after` record what changed, who changed it, and when.

## Scope mapping

- SAP fuel rows become Scope 1 combustion activity.
- Utility electricity rows become Scope 2 purchased electricity.
- SAP procurement rows become Scope 3 purchased goods.
- Travel rows become Scope 3 business travel.

This split makes scope an explicit normalized field instead of something inferred later from free text.

## Unit normalization

Rows keep both original and normalized quantities:

- `original_quantity`, `original_unit`
- `normalized_quantity`, `normalized_unit`

The normalizer currently supports liters, gallons, cubic meters, kilograms, kWh, USD spend, kilometers, passenger-kilometers, and hotel nights. Unsupported units fail at raw-record level instead of producing misleading emissions.

## Approval and audit lock

Analysts review rows with flags and quality scores. Approval sets:

- `status = approved`
- `locked_for_audit = true`
- `approved_by`
- `approved_at`

Approved rows cannot be edited or rejected through the API. Rows with error-level flags are blocked from approval until corrected or rejected. Warning-level flags can be approved because real analyst workflows often accept explainable anomalies.

## Why one normalized activity table

I considered separate tables for fuel, electricity, procurement, flights, hotels, and ground transport. I chose one `ActivityRecord` table because the review and audit workflow is the same across categories: quantity, factor, CO2e, source reference, flags, status, approval. Category-specific fields remain in `RawRecord.payload` and can later be promoted into typed child tables if reporting needs demand it.

