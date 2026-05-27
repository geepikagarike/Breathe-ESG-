import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from dateutil import parser

from .models import ActivityRecord, EmissionFactor, Facility, IngestionBatch, RawRecord


AIRPORT_COORDS = {
    "SFO": (37.6213, -122.3790),
    "JFK": (40.6413, -73.7781),
    "LHR": (51.4700, -0.4543),
    "FRA": (50.0379, 8.5622),
    "BLR": (13.1986, 77.7066),
    "DEL": (28.5562, 77.1000),
    "SEA": (47.4502, -122.3088),
    "ORD": (41.9742, -87.9073),
}

SAP_HEADER_ALIASES = {
    "MaterialDocument": "document_id",
    "Materialbeleg": "document_id",
    "Document": "document_id",
    "MaterialDocumentItem": "line_id",
    "Position": "line_id",
    "Plant": "plant_code",
    "Werk": "plant_code",
    "PostingDate": "posting_date",
    "Buchungsdatum": "posting_date",
    "Material": "material",
    "MaterialDescription": "description",
    "Materialkurztext": "description",
    "MovementType": "movement_type",
    "Bewegungsart": "movement_type",
    "QuantityInEntryUnit": "quantity",
    "Menge": "quantity",
    "EntryUnit": "unit",
    "ErfassME": "unit",
    "AmountInCompanyCodeCurrency": "amount",
    "BetragHauswaehrung": "amount",
    "CompanyCodeCurrency": "currency",
    "Hauswaehrung": "currency",
    "GLAccount": "gl_account",
    "Sachkonto": "gl_account",
    "ProcurementCategory": "procurement_category",
}

UNIT_ALIASES = {
    "l": "l",
    "liter": "l",
    "litre": "l",
    "gal": "gal",
    "gallon": "gal",
    "m3": "m3",
    "kg": "kg",
    "kwh": "kwh",
    "kw h": "kwh",
    "usd": "usd",
    "$": "usd",
    "km": "km",
    "night": "night",
}


@dataclass
class NormalizedRow:
    source_reference: str
    activity_type: str
    category: str
    scope: str
    activity_start: date
    activity_end: date
    original_quantity: Decimal
    original_unit: str
    normalized_quantity: Decimal
    normalized_unit: str
    factor_key: str
    facility_code: str | None = None
    flags: list | None = None


class RowError(Exception):
    pass


def checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def parse_date(value) -> date:
    if not value:
        raise RowError("missing date")
    return parser.parse(str(value), dayfirst="/" in str(value)).date()


def decimalish(value, field_name="quantity") -> Decimal:
    if value in (None, ""):
        raise RowError(f"missing {field_name}")
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        raise RowError(f"invalid {field_name}: {value}")


def normalize_unit(unit: str) -> str:
    key = str(unit or "").strip().lower()
    if key not in UNIT_ALIASES:
        raise RowError(f"unsupported unit: {unit}")
    return UNIT_ALIASES[key]


def convert_quantity(quantity: Decimal, unit: str, target_unit: str) -> Decimal:
    unit = normalize_unit(unit)
    if unit == target_unit:
        return quantity
    if unit == "gal" and target_unit == "l":
        return quantity * Decimal("3.785411784")
    raise RowError(f"cannot convert {unit} to {target_unit}")


def haversine_km(origin: str, destination: str) -> Decimal:
    if origin not in AIRPORT_COORDS or destination not in AIRPORT_COORDS:
        raise RowError(f"unknown airport code pair: {origin}-{destination}")
    lat1, lon1 = AIRPORT_COORDS[origin]
    lat2, lon2 = AIRPORT_COORDS[destination]
    radius_km = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return Decimal(str(2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a)))).quantize(Decimal("0.001"))


def read_csv(content: bytes):
    text = content.decode("utf-8-sig")
    sample = text[:4096]
    dialect = csv.Sniffer().sniff(sample) if "," in sample or ";" in sample else csv.excel
    return list(csv.DictReader(io.StringIO(text), dialect=dialect))


def canonicalize_sap_row(row):
    canonical = {}
    for key, value in row.items():
        canonical[SAP_HEADER_ALIASES.get(key.strip(), key.strip())] = value.strip() if isinstance(value, str) else value
    return canonical


def normalize_sap(row) -> NormalizedRow:
    data = canonicalize_sap_row(row)
    doc_id = data.get("document_id") or "SAP-UNKNOWN"
    line_id = data.get("line_id") or "0001"
    posting_date = parse_date(data.get("posting_date"))
    quantity = decimalish(data.get("quantity"), "quantity")
    unit = normalize_unit(data.get("unit"))
    plant_code = data.get("plant_code")
    material = (data.get("material") or data.get("description") or "").lower()
    category = data.get("procurement_category") or data.get("description") or data.get("material") or "SAP material"

    if any(token in material for token in ["diesel", "gasoline", "natural gas"]):
        target_unit = "m3" if "natural gas" in material else "l"
        factor = "natural_gas_m3" if target_unit == "m3" else "diesel_l"
        normalized_qty = convert_quantity(quantity, unit, target_unit)
        activity_type = "stationary_combustion" if "natural gas" in material else "mobile_combustion"
        scope = "scope1"
    else:
        amount = data.get("amount")
        if amount:
            quantity = decimalish(amount, "amount")
            unit = normalize_unit(data.get("currency") or "USD")
            normalized_qty = quantity
            target_unit = "usd"
            factor = "procurement_spend_usd"
        else:
            target_unit = "kg"
            normalized_qty = convert_quantity(quantity, unit, target_unit)
            factor = "procurement_material_kg"
        activity_type = "purchased_goods"
        scope = "scope3"

    flags = []
    if not plant_code:
        flags.append({"severity": "error", "code": "missing_plant", "message": "SAP row has no plant/Werk code"})
    if quantity <= 0:
        flags.append({"severity": "error", "code": "non_positive_quantity", "message": "Quantity must be positive"})

    return NormalizedRow(
        source_reference=f"{doc_id}/{line_id}",
        activity_type=activity_type,
        category=category,
        scope=scope,
        activity_start=posting_date,
        activity_end=posting_date,
        original_quantity=quantity,
        original_unit=unit,
        normalized_quantity=normalized_qty,
        normalized_unit=target_unit,
        factor_key=factor,
        facility_code=plant_code,
        flags=flags,
    )


def normalize_utility(row) -> NormalizedRow:
    start = parse_date(row.get("billing_period_start") or row.get("period_start"))
    end = parse_date(row.get("billing_period_end") or row.get("period_end"))
    qty = decimalish(row.get("usage") or row.get("kwh"), "usage")
    unit = normalize_unit(row.get("unit") or "kWh")
    normalized_qty = convert_quantity(qty, unit, "kwh")
    flags = []
    if normalized_qty <= 0:
        flags.append({"severity": "error", "code": "non_positive_usage", "message": "Electricity usage must be positive"})
    if (end - start).days > 45:
        flags.append({"severity": "warning", "code": "long_billing_period", "message": "Billing period is longer than 45 days"})
    demand = row.get("demand_kw")
    if demand and decimalish(demand, "demand_kw") > 5000:
        flags.append({"severity": "warning", "code": "high_peak_demand", "message": "Peak demand is high for a single meter"})

    return NormalizedRow(
        source_reference=row.get("meter_id") or row.get("account_number") or "utility-meter",
        activity_type="purchased_electricity",
        category=row.get("tariff") or "electricity",
        scope="scope2",
        activity_start=start,
        activity_end=end,
        original_quantity=qty,
        original_unit=unit,
        normalized_quantity=normalized_qty,
        normalized_unit="kwh",
        factor_key="electricity_us_grid_kwh",
        facility_code=row.get("facility_code") or row.get("plant_code"),
        flags=flags,
    )


def normalize_travel_segment(trip, segment, index) -> NormalizedRow:
    seg_type = (segment.get("type") or segment.get("segmentType") or "").lower()
    start = parse_date(segment.get("startDate") or segment.get("StartDateLocal") or trip.get("startDate"))
    end = parse_date(segment.get("endDate") or segment.get("EndDateLocal") or trip.get("endDate") or start)
    flags = []

    if seg_type in {"air", "flight"}:
        origin = segment.get("origin") or segment.get("StartCityCode") or segment.get("DepAirp")
        destination = segment.get("destination") or segment.get("EndCityCode") or segment.get("ArrAirp")
        distance = segment.get("distanceKm") or segment.get("distance_km")
        qty = decimalish(distance, "distanceKm") if distance else haversine_km(origin, destination)
        cabin = (segment.get("cabin") or segment.get("Cabin") or "economy").lower()
        multiplier = Decimal("1.50") if cabin in {"business", "first"} else Decimal("1.00")
        if not distance:
            flags.append({"severity": "warning", "code": "estimated_distance", "message": f"Distance estimated from airport codes {origin}-{destination}"})
        return NormalizedRow(
            source_reference=f"{trip.get('id', 'trip')}/air/{index}",
            activity_type="business_travel_air",
            category=f"flight_{cabin}",
            scope="scope3",
            activity_start=start,
            activity_end=end,
            original_quantity=qty,
            original_unit="km",
            normalized_quantity=qty * multiplier,
            normalized_unit="passenger_km",
            factor_key="flight_passenger_km",
            flags=flags,
        )

    if seg_type == "hotel":
        nights = segment.get("nights")
        qty = decimalish(nights, "nights") if nights else Decimal(max((end - start).days, 1))
        return NormalizedRow(
            source_reference=f"{trip.get('id', 'trip')}/hotel/{index}",
            activity_type="business_travel_hotel",
            category=segment.get("country") or segment.get("EndCountry") or "hotel",
            scope="scope3",
            activity_start=start,
            activity_end=end,
            original_quantity=qty,
            original_unit="night",
            normalized_quantity=qty,
            normalized_unit="night",
            factor_key="hotel_night",
            flags=flags,
        )

    if seg_type in {"ground", "car", "taxi", "rail"}:
        qty = decimalish(segment.get("distanceKm") or segment.get("distance_km"), "distanceKm")
        mode = (segment.get("mode") or seg_type).lower()
        key = "rail_km" if mode == "rail" else "ground_transport_km"
        return NormalizedRow(
            source_reference=f"{trip.get('id', 'trip')}/ground/{index}",
            activity_type="business_travel_ground",
            category=mode,
            scope="scope3",
            activity_start=start,
            activity_end=end,
            original_quantity=qty,
            original_unit="km",
            normalized_quantity=qty,
            normalized_unit="km",
            factor_key=key,
            flags=flags,
        )

    raise RowError(f"unsupported travel segment type: {seg_type}")


def quality_score(flags):
    score = 100
    for flag in flags:
        score -= 35 if flag.get("severity") == "error" else 12
    return max(score, 0)


def create_activity(tenant, batch, raw, normalized: NormalizedRow):
    factor = EmissionFactor.objects.get(key=normalized.factor_key)
    flags = normalized.flags or []
    facility = None
    if normalized.facility_code:
        facility = Facility.objects.filter(tenant=tenant, code=normalized.facility_code).first()
        if not facility:
            flags.append({"severity": "warning", "code": "unknown_facility", "message": f"No lookup for facility {normalized.facility_code}"})

    kg_co2e = normalized.normalized_quantity * factor.kg_co2e_per_unit
    if kg_co2e > Decimal("50000"):
        flags.append({"severity": "warning", "code": "large_emissions", "message": "Emissions exceed 50 tCO2e in a single row"})

    return ActivityRecord.objects.create(
        tenant=tenant,
        raw_record=raw,
        facility=facility,
        source_type=batch.connector.source_type,
        source_reference=normalized.source_reference,
        activity_type=normalized.activity_type,
        category=normalized.category[:120],
        scope=normalized.scope,
        activity_start=normalized.activity_start,
        activity_end=normalized.activity_end,
        original_quantity=normalized.original_quantity,
        original_unit=normalized.original_unit,
        normalized_quantity=normalized.normalized_quantity,
        normalized_unit=normalized.normalized_unit,
        emission_factor=factor,
        kg_co2e=kg_co2e,
        data_quality_score=quality_score(flags),
        flags=flags,
    )


def ingest_content(tenant, connector, filename, content: bytes):
    batch = IngestionBatch.objects.create(
        tenant=tenant,
        connector=connector,
        filename=filename,
        source_checksum=checksum(content),
    )
    accepted = 0
    failed = 0

    if connector.source_type in {"sap", "utility"}:
        rows = read_csv(content)
        batch.row_count = len(rows)
        batch.save(update_fields=["row_count"])
        normalizer = normalize_sap if connector.source_type == "sap" else normalize_utility
        for index, row in enumerate(rows, start=1):
            raw = RawRecord.objects.create(batch=batch, source_row_id=str(index), payload=row)
            try:
                normalized = normalizer(row)
                create_activity(tenant, batch, raw, normalized)
                accepted += 1
            except Exception as exc:
                raw.parse_status = "failed"
                raw.parse_errors = [str(exc)]
                raw.save(update_fields=["parse_status", "parse_errors"])
                failed += 1
    elif connector.source_type == "travel":
        payload = json.loads(content.decode("utf-8"))
        trips = payload.get("data", payload if isinstance(payload, list) else [])
        row_count = 0
        for trip in trips:
            for index, segment in enumerate(trip.get("segments", []), start=1):
                row_count += 1
                raw = RawRecord.objects.create(batch=batch, source_row_id=f"{trip.get('id', 'trip')}-{index}", payload={"trip": trip, "segment": segment})
                try:
                    normalized = normalize_travel_segment(trip, segment, index)
                    create_activity(tenant, batch, raw, normalized)
                    accepted += 1
                except Exception as exc:
                    raw.parse_status = "failed"
                    raw.parse_errors = [str(exc)]
                    raw.save(update_fields=["parse_status", "parse_errors"])
                    failed += 1
        batch.row_count = row_count
        batch.save(update_fields=["row_count"])
    else:
        raise RowError(f"unknown connector type: {connector.source_type}")

    batch.mark_processed(accepted, failed)
    return batch

