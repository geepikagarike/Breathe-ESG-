from rest_framework import serializers

from .models import ActivityRecord, AuditEvent, EmissionFactor, Facility, IngestionBatch, RawRecord, SourceConnector, Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name", "slug"]


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ["id", "code", "name", "country", "region", "grid_region"]


class SourceConnectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceConnector
        fields = ["id", "source_type", "name", "ingestion_mode", "config", "created_at"]


class EmissionFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionFactor
        fields = ["key", "source", "unit", "kg_co2e_per_unit", "scope", "meta"]


class IngestionBatchSerializer(serializers.ModelSerializer):
    connector = SourceConnectorSerializer()

    class Meta:
        model = IngestionBatch
        fields = [
            "id",
            "connector",
            "filename",
            "status",
            "received_at",
            "processed_at",
            "row_count",
            "accepted_count",
            "failed_count",
            "notes",
        ]


class RawRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawRecord
        fields = ["source_row_id", "payload", "parse_status", "parse_errors"]


class ActivityRecordSerializer(serializers.ModelSerializer):
    facility = FacilitySerializer()
    emission_factor = EmissionFactorSerializer()
    raw_record = RawRecordSerializer()

    class Meta:
        model = ActivityRecord
        fields = [
            "id",
            "source_type",
            "source_reference",
            "activity_type",
            "category",
            "scope",
            "facility",
            "activity_start",
            "activity_end",
            "original_quantity",
            "original_unit",
            "normalized_quantity",
            "normalized_unit",
            "emission_factor",
            "kg_co2e",
            "data_quality_score",
            "flags",
            "status",
            "locked_for_audit",
            "edited_by",
            "edited_at",
            "approved_by",
            "approved_at",
            "raw_record",
            "created_at",
            "updated_at",
        ]


class ActivityUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityRecord
        fields = ["category", "activity_start", "activity_end", "normalized_quantity", "normalized_unit", "flags"]


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ["id", "activity_record", "actor", "action", "before", "after", "reason", "created_at"]

