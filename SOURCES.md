# SOURCES.md

## SAP fuel and procurement

Researched format: SAP S/4HANA Material Document OData / material document export.

Useful references:

- SAP API Business Hub: `API_MATERIAL_DOCUMENT_SRV` material document API, https://api.sap.com/api/API_MATERIAL_DOCUMENT_SRV/overview
- SAP Help Portal, S/4HANA material documents and goods movements, https://help.sap.com/

What I learned:

SAP exports are often operational rather than analyst-friendly. Useful fields come from material documents and goods movements: material document number, item, plant, posting date, material, movement type, quantity, unit, GL account, amount, and currency. Plant codes need a lookup table. Headers can differ by configuration and language, so the normalizer maps English and German column names.

Sample data:

`sample-data/sap_material_documents.csv` includes diesel, natural gas, steel procurement, a missing plant code, and spend-based laptop procurement. It intentionally mixes date formats and includes a German-style date to force normalization.

What would break in production:

- Material descriptions are not reliable category classifiers.
- SAP units may include custom UoM codes.
- Procurement should usually join material master, purchase order, invoice, supplier, and cost center data.
- Delta extraction needs source timestamps or change pointers.

## Utility electricity

Researched format: Green Button / utility portal CSV export.

Useful references:

- Green Button Alliance standard overview, https://www.greenbuttonalliance.org/
- U.S. Department of Energy Green Button overview, https://www.energy.gov/data/green-button

What I learned:

Utility exports typically identify account, meter, service address, billing period, readings, usage, units, tariff, demand, charges, and currency. Billing periods do not align to calendar months, which matters because monthly carbon reporting should not assume one row equals one calendar month.

Sample data:

`sample-data/utility_green_button.csv` has two industrial monthly readings, one office bill spanning nearly two months, and a zero-usage meter. The long period and zero usage become review signals.

What would break in production:

- PDF bills need OCR/table extraction and confidence scoring.
- Green Button XML is nested and more complex than the CSV used here.
- Market-based Scope 2 requires supplier contracts or energy attribute certificates.
- Interval data and demand charges need different aggregation rules.

## Corporate travel

Researched format: SAP Concur Travel Itinerary API and expense/travel segment shape.

Useful references:

- SAP Concur Itinerary API v4, https://developer.concur.com/api-reference/travel/itinerary-v4/v4.itinerary.html
- SAP Concur developer API reference, https://developer.concur.com/api-reference/

What I learned:

Travel data is naturally trip-based and nested. Air, hotel, car, and rail segments carry different fields and require different emission factors. Flight distances may not be present, so airport-code distance estimation is a realistic fallback. Hotels can be expressed as explicit nights or inferred from start and end dates.

Sample data:

`sample-data/concur_travel_export.json` includes two trips with air, hotel, taxi, and rail segments. One flight omits distance so the app estimates it from airport codes. Another uses business class and applies a multiplier.

What would break in production:

- Airport code coverage needs a complete maintained database.
- Cancellations and changed tickets must be reconciled.
- Travel booking data and expense data may disagree.
- Distance methodology should be agreed with auditors.

