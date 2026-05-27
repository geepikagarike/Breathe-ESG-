from django.contrib import admin

from .models import ActivityRecord, AuditEvent, EmissionFactor, Facility, IngestionBatch, RawRecord, SourceConnector, Tenant

admin.site.register(Tenant)
admin.site.register(Facility)
admin.site.register(SourceConnector)
admin.site.register(IngestionBatch)
admin.site.register(RawRecord)
admin.site.register(EmissionFactor)
admin.site.register(ActivityRecord)
admin.site.register(AuditEvent)

