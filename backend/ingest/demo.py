from pathlib import Path

from django.db import transaction

from .models import ActivityRecord, AuditEvent, EmissionFactor, Facility, IngestionBatch, RawRecord, SourceConnector, Tenant
from .normalization import ingest_content

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = ROOT / "sample-data"


FACTORS = [
    ("diesel_l", "EPA/IPCC-style prototype factor", "l", "2.680000", "scope1", {"fuel": "diesel"}),
    ("natural_gas_m3", "EPA/IPCC-style prototype factor", "m3", "2.020000", "scope1", {"fuel": "natural gas"}),
    ("electricity_us_grid_kwh", "EPA eGRID-style prototype factor", "kwh", "0.386000", "scope2", {"grid": "US average"}),
    ("procurement_spend_usd", "Spend-based EEIO placeholder", "usd", "0.420000", "scope3", {"method": "spend"}),
    ("procurement_material_kg", "Material-based placeholder", "kg", "1.900000", "scope3", {"method": "mass"}),
    ("flight_passenger_km", "DEFRA/ICAO-style prototype factor", "passenger_km", "0.158000", "scope3", {"mode": "air"}),
    ("hotel_night", "Hotel footprint prototype factor", "night", "22.000000", "scope3", {"mode": "hotel"}),
    ("ground_transport_km", "Taxi/rental car prototype factor", "km", "0.180000", "scope3", {"mode": "ground"}),
    ("rail_km", "Rail prototype factor", "km", "0.041000", "scope3", {"mode": "rail"}),
]


def ensure_reference_data():
    tenant, _ = Tenant.objects.get_or_create(slug="acme-industrials", defaults={"name": "Acme Industrials"})
    for code, name, region, grid in [
        ("1000", "Fremont Assembly Plant", "CA", "CAMX"),
        ("DE01", "Munich Components", "BY", "DE"),
        ("NYC1", "New York Office", "NY", "NYUP"),
    ]:
        Facility.objects.get_or_create(
            tenant=tenant,
            code=code,
            defaults={"name": name, "country": "US" if code != "DE01" else "DE", "region": region, "grid_region": grid},
        )

    connectors = {
        "sap": SourceConnector.objects.get_or_create(
            tenant=tenant,
            source_type="sap",
            name="SAP S/4HANA Material Documents CSV",
            defaults={"ingestion_mode": "file_upload", "config": {"service": "API_MATERIAL_DOCUMENT_SRV"}},
        )[0],
        "utility": SourceConnector.objects.get_or_create(
            tenant=tenant,
            source_type="utility",
            name="Utility portal Green Button CSV",
            defaults={"ingestion_mode": "file_upload", "config": {"format": "green-button-inspired-csv"}},
        )[0],
        "travel": SourceConnector.objects.get_or_create(
            tenant=tenant,
            source_type="travel",
            name="SAP Concur itinerary JSON export",
            defaults={"ingestion_mode": "api_pull_or_json_export", "config": {"endpoint": "/travel/v4/trips"}},
        )[0],
    }

    for key, source, unit, factor, scope, meta in FACTORS:
        EmissionFactor.objects.update_or_create(
            key=key,
            defaults={"source": source, "unit": unit, "kg_co2e_per_unit": factor, "scope": scope, "meta": meta},
        )

    return tenant, connectors


@transaction.atomic
def seed_demo(reset=True):
    tenant, connectors = ensure_reference_data()
    if reset:
        ActivityRecord.objects.filter(tenant=tenant).delete()
        RawRecord.objects.filter(batch__tenant=tenant).delete()
        IngestionBatch.objects.filter(tenant=tenant).delete()
        AuditEvent.objects.filter(tenant=tenant).delete()

    files = {
        "sap": "sap_material_documents.csv",
        "utility": "utility_green_button.csv",
        "travel": "concur_travel_export.json",
    }
    batches = []
    for source_type, filename in files.items():
        content = (SAMPLE_DIR / filename).read_bytes()
        batches.append(ingest_content(tenant, connectors[source_type], filename, content))
    return tenant, batches
