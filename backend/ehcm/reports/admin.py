from django.contrib import admin
from .models import QuarterlyReport, ReportAttachment


@admin.register(QuarterlyReport)
class QuarterlyReportAdmin(admin.ModelAdmin):
    list_display = ("consul", "year", "quarter", "version", "status", "receipt_number", "submitted_at")
    list_filter = ("year", "quarter", "status")
    search_fields = ("consul__user__full_name", "receipt_number")


@admin.register(ReportAttachment)
class ReportAttachmentAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "report", "file_size_bytes", "uploaded_by", "uploaded_at")
