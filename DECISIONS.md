# DECISIONS.md

## SAP source choice

I chose a flattened SAP S/4HANA Material Document OData export represented as CSV. The handled subset is goods movements for fuel and procurement materials from `API_MATERIAL_DOCUMENT_SRV`-style data.

Why: enterprise onboarding teams often cannot get a clean real-time SAP integration on day one, but they can usually export material document data. Material documents also carry fields needed for emissions normalization: plant, posting date, material, movement type, quantity, unit, amount, currency, and GL account.

Handled:

- English and German header aliases such as `Plant` and `Werk`, `PostingDate` and `Buchungsdatum`.
- Fuel rows by material description, mapped to Scope 1.
- Procurement rows by amount or mass, mapped to Scope 3.
- Liters, gallons, cubic meters, kilograms, and USD spend.
- Missing plant codes and unsupported units as review flags or parse failures.

Ignored:

- IDoc parsing.
- BAPI calls.
- SAP authorization and delta extraction.
- Full material master enrichment.
- Purchase order three-way matching.

PM question: Which SAP object is the contractual source of truth for procurement emissions: material documents, purchase orders, invoices, or spend cubes?

## Utility source choice

I chose a Green Button-style utility portal CSV for electricity.

Why: facilities teams commonly download meter or bill CSVs from utility portals before API access exists. Green Button also reflects a realistic mental model: account, meter, usage, units, reading period, demand, tariff, and charges.

Handled:

- kWh usage.
- Account and meter identifiers.
- Billing periods that do not align to calendar months.
- Demand and tariff fields retained in raw payload.
- Zero usage as an error.
- Billing periods longer than 45 days as suspicious.

Ignored:

- PDF bill extraction.
- Interval data at 15-minute granularity.
- Utility-specific API OAuth flows.
- Market-based Scope 2 using supplier-specific emission factors.

PM question: Do analysts need location-based Scope 2 only, market-based Scope 2, or both?

## Travel source choice

I chose a Concur-style itinerary JSON export with trips and segments.

Why: travel platforms expose trips as nested itineraries with air, hotel, rail, and car segments. The data is not naturally a flat table, and distances are sometimes missing.

Handled:

- Air, hotel, taxi/car, and rail segments.
- Flight distance supplied by the source or estimated from airport codes.
- Cabin multiplier for business/first class.
- Hotel nights supplied or inferred from dates.
- Ground transport by kilometers.

Ignored:

- Traveler identity workflows.
- Expense report approval state.
- Airport database beyond a tiny demo map.
- Radiative forcing and class-specific factors beyond a simple multiplier.
- Multi-leg ticket proration.

PM question: Should travel emissions be based on booked itinerary, expensed receipts, or completed trips after cancellations?

## Analyst UX choice

The UI is a review workbench, not a generic CRUD app. The first screen shows batch health, source filters, suspicious rows, raw payload, and approve/reject actions. The analyst can reload demo data and upload new source files.

## Auth choice

The prototype records reviewer identity using an `X-Analyst-Email` header. Real auth is deliberately omitted because deployment and source modeling are higher-value for this assignment. The model supports a real user foreign key later.

