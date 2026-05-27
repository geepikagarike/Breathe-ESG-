from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .demo import ensure_reference_data, seed_demo
from .models import ActivityRecord, AuditEvent, IngestionBatch, SourceConnector, Tenant
from .normalization import ingest_content
from .serializers import ActivityRecordSerializer, ActivityUpdateSerializer, IngestionBatchSerializer, TenantSerializer


def tenant_from_request(request):
    slug = request.query_params.get("tenant") or request.data.get("tenant") or "acme-industrials"
    tenant, _ = Tenant.objects.get_or_create(slug=slug, defaults={"name": slug.replace("-", " ").title()})
    return tenant


def analyst_email(request):
    return request.headers.get("X-Analyst-Email") or "analyst@breatheesg.com"


class TenantList(generics.ListAPIView):
    queryset = Tenant.objects.all().order_by("name")
    serializer_class = TenantSerializer


class DashboardView(APIView):
    def get(self, request):
        tenant = tenant_from_request(request)
        qs = ActivityRecord.objects.filter(tenant=tenant)
        totals = qs.aggregate(total_kg=Sum("kg_co2e"), rows=Count("id"))
        by_status = dict(qs.values_list("status").annotate(count=Count("id")))
        by_scope = list(qs.values("scope").annotate(kg_co2e=Sum("kg_co2e"), rows=Count("id")).order_by("scope"))
        by_source = list(qs.values("source_type").annotate(kg_co2e=Sum("kg_co2e"), rows=Count("id")).order_by("source_type"))
        flagged = qs.filter(~Q(flags=[])).count()
        latest_batches = IngestionBatch.objects.filter(tenant=tenant).order_by("-received_at")[:5]
        return Response(
            {
                "tenant": TenantSerializer(tenant).data,
                "total_kg_co2e": totals["total_kg"] or Decimal("0"),
                "rows": totals["rows"],
                "flagged_rows": flagged,
                "by_status": by_status,
                "by_scope": by_scope,
                "by_source": by_source,
                "latest_batches": IngestionBatchSerializer(latest_batches, many=True).data,
            }
        )


class BatchList(generics.ListAPIView):
    serializer_class = IngestionBatchSerializer

    def get_queryset(self):
        tenant = tenant_from_request(self.request)
        return IngestionBatch.objects.filter(tenant=tenant).select_related("connector").order_by("-received_at")


class ActivityRecordList(generics.ListAPIView):
    serializer_class = ActivityRecordSerializer

    def get_queryset(self):
        tenant = tenant_from_request(self.request)
        qs = (
            ActivityRecord.objects.filter(tenant=tenant)
            .select_related("facility", "emission_factor", "raw_record")
            .order_by("-created_at", "-id")
        )
        for key in ["status", "source_type", "scope"]:
            value = self.request.query_params.get(key)
            if value:
                qs = qs.filter(**{key: value})
        if self.request.query_params.get("flagged") == "1":
            qs = qs.exclude(flags=[])
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(source_reference__icontains=search) | Q(category__icontains=search) | Q(activity_type__icontains=search))
        return qs


class ActivityRecordDetail(generics.RetrieveUpdateAPIView):
    serializer_class = ActivityRecordSerializer

    def get_queryset(self):
        tenant = tenant_from_request(self.request)
        return ActivityRecord.objects.filter(tenant=tenant).select_related("facility", "emission_factor", "raw_record")

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.locked_for_audit:
            return Response({"detail": "Approved records are locked for audit."}, status=status.HTTP_409_CONFLICT)
        before = ActivityRecordSerializer(instance).data
        serializer = ActivityUpdateSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save(edited_by=analyst_email(request), edited_at=timezone.now())
        AuditEvent.objects.create(
            tenant=updated.tenant,
            activity_record=updated,
            actor=analyst_email(request),
            action="edited",
            before=before,
            after=ActivityRecordSerializer(updated).data,
            reason=request.data.get("reason", ""),
        )
        return Response(ActivityRecordSerializer(updated).data)


class ApproveActivity(APIView):
    def post(self, request, pk):
        tenant = tenant_from_request(request)
        record = ActivityRecord.objects.get(pk=pk, tenant=tenant)
        before = ActivityRecordSerializer(record).data
        if any(flag.get("severity") == "error" for flag in record.flags):
            return Response({"detail": "Resolve error flags before approval."}, status=status.HTTP_409_CONFLICT)
        record.approve(analyst_email(request))
        AuditEvent.objects.create(
            tenant=tenant,
            activity_record=record,
            actor=analyst_email(request),
            action="approved",
            before=before,
            after=ActivityRecordSerializer(record).data,
            reason=request.data.get("reason", "Analyst approved"),
        )
        return Response(ActivityRecordSerializer(record).data)


class RejectActivity(APIView):
    def post(self, request, pk):
        tenant = tenant_from_request(request)
        record = ActivityRecord.objects.get(pk=pk, tenant=tenant)
        if record.locked_for_audit:
            return Response({"detail": "Approved records are locked for audit."}, status=status.HTTP_409_CONFLICT)
        before = ActivityRecordSerializer(record).data
        record.status = ActivityRecord.Status.REJECTED
        record.edited_by = analyst_email(request)
        record.edited_at = timezone.now()
        record.save(update_fields=["status", "edited_by", "edited_at", "updated_at"])
        AuditEvent.objects.create(
            tenant=tenant,
            activity_record=record,
            actor=analyst_email(request),
            action="rejected",
            before=before,
            after=ActivityRecordSerializer(record).data,
            reason=request.data.get("reason", "Rejected by analyst"),
        )
        return Response(ActivityRecordSerializer(record).data)


class UploadIngestion(APIView):
    def post(self, request):
        tenant = tenant_from_request(request)
        ensure_reference_data()
        source_type = request.data.get("source_type")
        upload = request.FILES.get("file")
        if source_type not in {"sap", "utility", "travel"}:
            return Response({"detail": "source_type must be sap, utility, or travel"}, status=status.HTTP_400_BAD_REQUEST)
        if not upload:
            return Response({"detail": "file is required"}, status=status.HTTP_400_BAD_REQUEST)
        connector = SourceConnector.objects.filter(tenant=tenant, source_type=source_type).first()
        if not connector:
            connector = SourceConnector.objects.create(tenant=tenant, source_type=source_type, name=f"{source_type} upload", ingestion_mode="file_upload")
        batch = ingest_content(tenant, connector, upload.name, upload.read())
        return Response(IngestionBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


class SeedDemo(APIView):
    def post(self, request):
        tenant, batches = seed_demo(reset=True)
        return Response(
            {
                "tenant": TenantSerializer(tenant).data,
                "batches": IngestionBatchSerializer(batches, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )

