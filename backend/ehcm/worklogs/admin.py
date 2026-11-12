from django.contrib import admin
from .models import WorkLogEntry


@admin.register(WorkLogEntry)
class WorkLogEntryAdmin(admin.ModelAdmin):
    list_display = ("activity_date", "title", "consul", "category", "status", "is_locked")
    list_filter = ("category", "status", "is_locked")
    search_fields = ("title", "consul__user__full_name")
