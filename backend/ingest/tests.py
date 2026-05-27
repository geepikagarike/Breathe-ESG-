from django.test import TestCase

from .demo import seed_demo
from .models import ActivityRecord, IngestionBatch, Tenant


class IngestionTests(TestCase):
    def test_demo_ingestion_creates_reviewable_records_and_failures(self):
        tenant, _ = seed_demo()
        self.assertEqual(Tenant.objects.count(), 1)
        self.assertEqual(IngestionBatch.objects.filter(tenant=tenant).count(), 3)
        self.assertGreater(ActivityRecord.objects.filter(tenant=tenant).count(), 5)
        self.assertTrue(
            any(
                flag.get("code") == "estimated_distance"
                for record in ActivityRecord.objects.filter(tenant=tenant)
                for flag in record.flags
            )
        )

    def test_error_flags_block_approval(self):
        tenant, _ = seed_demo()
        record = next(
            (
                item
                for item in ActivityRecord.objects.filter(tenant=tenant)
                if any(flag.get("code") == "missing_plant" for flag in item.flags)
            ),
            None,
        )
        self.assertIsNotNone(record)
        self.assertEqual(record.status, ActivityRecord.Status.NEEDS_REVIEW)
