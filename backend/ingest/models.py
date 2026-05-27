from django.db import models
from django.utils import timezone


class Tenant(models.Model):
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Facility(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="facilities")
    code = models.CharField(max_length=60)
    name = models.CharField(max_length=180)
    country = models.CharField(max_length=2, default="US")
    region = models.CharField(max_length=80, blank=True)
    grid_region = models.CharField(max_length=80, blank=True)

    class Meta:
        unique_together = [("tenant", "code")]

    def __str__(self):
        return f"{self.code} - {self.name}"


class SourceConnector(models.Model):
    class SourceType(models.TextChoices):
        SAP = "sap", "SAP"
        UTILITY = "utility", "Utility"
        TRAVEL = "travel", "Travel"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="connectors")
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    name = models.CharField(max_length=180)
    ingestion_mode = models.CharField(max_length=80)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("tenant", "source_type", "name")]

    def __str__(self):
        return f"{self.tenant.slug}:{self.source_type}:{self.name}"


class IngestionBatch(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="batches")
    connector = models.ForeignKey(SourceConnector, on_delete=models.PROTECT, related_name="batches")
    filename = models.CharField(max_length=255)
    source_checksum = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    accepted_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    def mark_processed(self, accepted_count, failed_count):
        self.status = self.Status.PROCESSED if failed_count == 0 else self.Status.FAILED if accepted_count == 0 else self.Status.PROCESSED
        self.processed_at = timezone.now()
        self.accepted_count = accepted_count
        self.failed_count = failed_count
        self.save(update_fields=["status", "processed_at", "accepted_count", "failed_count"])


class RawRecord(models.Model):
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name="raw_records")
    source_row_id = models.CharField(max_length=180)
    payload = models.JSONField(default=dict)
    parse_status = models.CharField(max_length=20, default="parsed")
    parse_errors = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("batch", "source_row_id")]


class EmissionFactor(models.Model):
    key = models.CharField(max_length=120, unique=True)
    source = models.CharField(max_length=180)
    unit = models.CharField(max_length=40)
    kg_co2e_per_unit = models.DecimalField(max_digits=14, decimal_places=6)
    scope = models.CharField(max_length=10)
    valid_from = models.DateField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.key


class ActivityRecord(models.Model):
    class Scope(models.TextChoices):
        SCOPE1 = "scope1", "Scope 1"
        SCOPE2 = "scope2", "Scope 2"
        SCOPE3 = "scope3", "Scope 3"

    class Status(models.TextChoices):
        NEEDS_REVIEW = "needs_review", "Needs review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        LOCKED = "locked", "Locked"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="activity_records")
    raw_record = models.ForeignKey(RawRecord, on_delete=models.PROTECT, related_name="activity_records")
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_records")
    source_type = models.CharField(max_length=20)
    source_reference = models.CharField(max_length=180)
    activity_type = models.CharField(max_length=80)
    category = models.CharField(max_length=120)
    scope = models.CharField(max_length=10, choices=Scope.choices)
    activity_start = models.DateField()
    activity_end = models.DateField()
    original_quantity = models.DecimalField(max_digits=18, decimal_places=6)
    original_unit = models.CharField(max_length=40)
    normalized_quantity = models.DecimalField(max_digits=18, decimal_places=6)
    normalized_unit = models.CharField(max_length=40)
    emission_factor = models.ForeignKey(EmissionFactor, on_delete=models.PROTECT, null=True, blank=True)
    kg_co2e = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    data_quality_score = models.PositiveSmallIntegerField(default=100)
    flags = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEEDS_REVIEW)
    locked_for_audit = models.BooleanField(default=False)
    edited_by = models.CharField(max_length=180, blank=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.CharField(max_length=180, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "source_type"]),
            models.Index(fields=["tenant", "scope"]),
        ]

    def approve(self, analyst_email):
        self.status = self.Status.APPROVED
        self.locked_for_audit = True
        self.approved_by = analyst_email
        self.approved_at = timezone.now()
        self.save(update_fields=["status", "locked_for_audit", "approved_by", "approved_at", "updated_at"])


class AuditEvent(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="audit_events")
    activity_record = models.ForeignKey(ActivityRecord, on_delete=models.CASCADE, related_name="audit_events", null=True, blank=True)
    actor = models.CharField(max_length=180)
    action = models.CharField(max_length=80)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

