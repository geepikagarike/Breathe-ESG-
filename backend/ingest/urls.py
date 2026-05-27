from django.urls import path

from . import views

urlpatterns = [
    path("tenants/", views.TenantList.as_view()),
    path("dashboard/", views.DashboardView.as_view()),
    path("batches/", views.BatchList.as_view()),
    path("activity-records/", views.ActivityRecordList.as_view()),
    path("activity-records/<int:pk>/", views.ActivityRecordDetail.as_view()),
    path("activity-records/<int:pk>/approve/", views.ApproveActivity.as_view()),
    path("activity-records/<int:pk>/reject/", views.RejectActivity.as_view()),
    path("ingestions/upload/", views.UploadIngestion.as_view()),
    path("ingestions/seed-demo/", views.SeedDemo.as_view()),
]

