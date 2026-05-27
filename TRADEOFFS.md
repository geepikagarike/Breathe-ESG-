# TRADEOFFS.md

## 1. No real source-system credentials

I did not build live SAP, utility, or Concur OAuth integrations. The prototype accepts realistic exports instead.

Reason: source integration setup would dominate the four-day prototype and require credentials the assignment does not provide. The harder judgment problem is the source shape, normalization, and review model, which the app demonstrates.

## 2. No full factor-management system

Emission factors are seeded as prototype constants instead of managed through a versioned admin workflow with geographic, temporal, and methodology selection.

Reason: factor governance is a product of its own. The data model keeps factor keys, units, scopes, metadata, and validity dates so proper factor management can be added without changing the review workflow.

## 3. No production authentication or row-level authorization

The demo uses a fixed analyst header and tenant query parameter.

Reason: production auth is important but not the main uncertainty in this assignment. Multi-tenancy is represented in the schema, and all querysets are tenant-filtered. A real deployment would add SSO, tenant membership, and role checks before auditors could rely on it.

