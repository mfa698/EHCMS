from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.models import (
    HonoraryConsul,
    AppointmentContract,
    PerformanceEvaluation,
    Recommendation,
    RenewalCase,
)
from worklogs.models import WorkLogEntry
from reports.models import QuarterlyReport, ReportAttachment
from notifications.models import Notification


def _quarter_label(year: int, quarter: int) -> str:
    return f"Q{quarter} {year}"


def _quarter_due_date(year: int, quarter: int) -> str:
    ends = {1: f"{year}-03-31", 2: f"{year}-06-30", 3: f"{year}-09-30", 4: f"{year}-12-31"}
    return ends.get(quarter, f"{year}-12-31")


def _parse_quarter(label: str):
    parts = str(label or "").strip().split()
    q = int(parts[0].replace("Q", "")) if parts else 4
    y = int(parts[1]) if len(parts) > 1 else timezone.localdate().year
    return y, q


def _scoped_consuls(user):
    qs = HonoraryConsul.objects.select_related("user", "mission", "mission__head_of_mission")
    if user.role == "consul":
        return qs.filter(user=user)
    if user.role == "ambassador":
        return qs.filter(mission__head_of_mission=user)
    return qs


def _notif_type(cat: str) -> str:
    c = (cat or "").lower()
    if "expiry" in c or "renewal" in c:
        return "expiry"
    if "report" in c:
        return "report"
    return "workflow"


def _serialize_notifications(user):
    return [
        {
            "id": str(n.id),
            "type": _notif_type(n.category),
            "title": n.title,
            "message": n.message,
            "date": n.created_at.strftime("%Y-%m-%d"),
            "read": n.is_read,
        }
        for n in Notification.objects.filter(recipient=user).order_by("-created_at")
    ]


class ConsulDashboardCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        consul = _scoped_consuls(request.user).first()
        if not consul:
            return Response({"error": "Consul profile not found."}, status=404)
        contract = AppointmentContract.objects.filter(consul=consul, is_current=True).first()
        today = timezone.localdate()
        curr_q = (today.month - 1) // 3 + 1
        latest_rep = QuarterlyReport.objects.filter(consul=consul).order_by("-year", "-quarter").first()
        logs = WorkLogEntry.objects.filter(consul=consul).order_by("-activity_date")[:5]
        unread = Notification.objects.filter(recipient=request.user, is_read=False).count()

        return Response({
            "user": {"name": request.user.full_name, "role": "honorary_consul"},
            "mission": f"{consul.cities_of_operation} ({consul.mission.name})" if consul.cities_of_operation else consul.mission.name,
            "contract": {
                "appointmentDate": str(consul.date_of_first_appointment) if consul.date_of_first_appointment else None,
                "endDate": str(contract.end_date) if contract else None,
                "daysRemaining": (contract.end_date - today).days if contract else None,
            },
            "nextReport": {"quarter": _quarter_label(today.year, curr_q), "dueDate": _quarter_due_date(today.year, curr_q)},
            "submission": {
                "quarter": _quarter_label(latest_rep.year, latest_rep.quarter),
                "status": latest_rep.status,
                "submittedAt": latest_rep.submitted_at.strftime("%Y-%m-%d") if latest_rep.submitted_at else None,
            } if latest_rep else {"quarter": _quarter_label(today.year, curr_q), "status": "not_started", "submittedAt": None},
            "unreadNotifications": unread,
            "recentActivity": [
                {"date": str(w.activity_date), "title": w.title, "status": "completed" if w.is_locked else "ongoing"}
                for w in logs
            ],
        })


class ConsulProfileCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def _payload(self, request, consul):
        contract = AppointmentContract.objects.filter(consul=consul, is_current=True).first()
        hom = consul.mission.head_of_mission
        cities = [c.strip() for c in (consul.cities_of_operation or "").split(",") if c.strip()]
        return {
            "fullName": request.user.full_name,
            "title": "Honorary Consul",
            "mission": consul.mission.name,
            "jurisdictions": cities,
            "headOfMission": hom.full_name if hom else "-",
            "appointmentDate": str(consul.date_of_first_appointment) if consul.date_of_first_appointment else None,
            "contractEndDate": str(contract.end_date) if contract else None,
            "email": request.user.email,
            "phone": request.user.phone_number,
            "officeAddress": consul.office_address or "",
        }

    def get(self, request):
        consul = _scoped_consuls(request.user).first()
        return Response(self._payload(request, consul))

    def patch(self, request):
        consul = _scoped_consuls(request.user).first()
        if "officeAddress" in request.data:
            consul.office_address = request.data["officeAddress"]
            consul.save(update_fields=["office_address", "updated_at"])
        if "phone" in request.data and request.data["phone"]:
            request.user.phone_number = request.data["phone"]
            request.user.save(update_fields=["phone_number"])
        return Response(self._payload(request, consul))
class NotificationsCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_serialize_notifications(request.user))


class NotificationReadCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        Notification.objects.filter(id=pk, recipient=request.user).update(is_read=True)
        return Response({"status": "read"})


class NotificationReadAllCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"status": "all_read"})


class WorkLogCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def _serialize(self, w):
        return {
            "id": str(w.id),
            "date": str(w.activity_date),
            "title": w.title,
            "notes": w.description,
            "status": "completed" if w.is_locked else "ongoing",
            "attachments": [w.evidence_file.name] if getattr(w, "evidence_file", None) else [],
        }

    def get(self, request):
        consul = _scoped_consuls(request.user).first()
        logs = WorkLogEntry.objects.filter(consul=consul).order_by("-activity_date")
        return Response([self._serialize(w) for w in logs])

    def post(self, request):
        consul = _scoped_consuls(request.user).first()
        w = WorkLogEntry.objects.create(
            consul=consul,
            activity_date=request.data.get("date") or timezone.localdate(),
            category="other",
            title=request.data.get("title", "Consular Activity"),
            description=request.data.get("notes", ""),
        )
        return Response(self._serialize(w), status=201)


class WorkLogDetailCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        w = WorkLogEntry.objects.filter(id=pk, consul__user=request.user).first()
        if not w:
            return Response(status=404)
        if w.is_locked:
            return Response({"error": "Locked entry"}, status=423)
        if "title" in request.data:
            w.title = request.data["title"]
        if "notes" in request.data:
            w.description = request.data["notes"]
        w.save()
        return Response({"id": str(w.id), "date": str(w.activity_date), "title": w.title, "notes": w.description, "status": "ongoing", "attachments": []})


class ConsulReportsCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def _serialize(self, r):
        q_label = _quarter_label(r.year, r.quarter)
        return {
            "id": str(r.id),
            "quarter": q_label,
            "dueDate": _quarter_due_date(r.year, r.quarter),
            "status": r.status if r.status != "draft" else "draft",
            "submittedAt": r.submitted_at.strftime("%Y-%m-%d") if r.submitted_at else None,
            "reference": r.receipt_number,
            "content": {
                "summary": r.executive_summary or "",
                "achievements": r.trade_and_investment or "",
                "challenges": "",
                "plans": r.diaspora_and_consular_services or "",
                "attachments": [a.original_filename for a in r.attachments.all()],
            },
        }

    def get(self, request):
        consul = _scoped_consuls(request.user).first()
        today = timezone.localdate()
        curr_q = (today.month - 1) // 3 + 1
        QuarterlyReport.objects.get_or_create(consul=consul, year=today.year, quarter=curr_q)
        reps = QuarterlyReport.objects.filter(consul=consul).order_by("-year", "-quarter")
        return Response([self._serialize(r) for r in reps])


class ConsulReportDraftCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        r = QuarterlyReport.objects.filter(id=pk, consul__user=request.user).first()
        if not r:
            return Response(status=404)
        if r.status in ("submitted", "endorsed"):
            return Response({"error": "Report is locked"}, status=423)
        r.executive_summary = request.data.get("summary", r.executive_summary)
        r.trade_and_investment = request.data.get("achievements", r.trade_and_investment)
        r.diaspora_and_consular_services = request.data.get("plans", r.diaspora_and_consular_services)
        r.status = "draft"
        r.save()
        for f in request.FILES.getlist("attachments"):
            ReportAttachment.objects.create(report=r, file=f, original_filename=f.name, file_size=f.size)
        return Response(ConsulReportsCompatView()._serialize(r))


class ConsulReportSubmitCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        r = QuarterlyReport.objects.filter(id=pk, consul__user=request.user).first()
        if not r:
            return Response(status=404)
        r.executive_summary = request.data.get("summary", r.executive_summary) or "Quarterly activities completed."
        r.trade_and_investment = request.data.get("achievements", r.trade_and_investment)
        r.diaspora_and_consular_services = request.data.get("plans", r.diaspora_and_consular_services)
        for f in request.FILES.getlist("attachments"):
            ReportAttachment.objects.create(report=r, file=f, original_filename=f.name, file_size=f.size)
        r.submit()
        return Response(ConsulReportsCompatView()._serialize(r))
def _hom_consul_rows(user):
    today = timezone.localdate()
    rows = []
    for c in _scoped_consuls(user):
        ct = AppointmentContract.objects.filter(consul=c, is_current=True).first()
        days = (ct.end_date - today).days if ct else 999
        last_log = WorkLogEntry.objects.filter(consul=c).order_by("-activity_date").first()
        latest_rep = QuarterlyReport.objects.filter(consul=c).order_by("-year", "-quarter").first()
        reasons = []
        if days <= 90:
            reasons.append("Contract expired" if days < 0 else f"Contract ends in {days} days")
        rows.append({
            "id": str(c.id),
            "name": c.user.full_name,
            "city": c.cities_of_operation or "-",
            "email": c.user.email,
            "phone": c.user.phone_number,
            "appointmentDate": str(c.date_of_first_appointment) if c.date_of_first_appointment else None,
            "contractEndDate": str(ct.end_date) if ct else None,
            "daysRemaining": days,
            "lastActivity": str(last_log.activity_date) if last_log else str(c.date_of_first_appointment or today),
            "entriesThisQuarter": WorkLogEntry.objects.filter(consul=c).count(),
            "reportStatus": latest_rep.status if latest_rep else "not_started",
            "attentionReasons": reasons,
        })
    return rows


class HomDashboardCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = _hom_consul_rows(request.user)
        att = [r for r in rows if r["attentionReasons"]]
        exp = [r for r in rows if r["daysRemaining"] <= 90]
        pending = QuarterlyReport.objects.filter(consul__mission__head_of_mission=request.user, status="submitted").count()
        mission = request.user.headed_missions.first()
        return Response({
            "user": {"name": request.user.full_name, "role": "head_of_mission"},
            "mission": mission.name if mission else "Diplomatic Mission",
            "totals": {"consuls": len(rows), "attention": len(att), "pendingReports": pending, "expiring": len(exp)},
            "attentionList": [{"id": r["id"], "name": r["name"], "city": r["city"], "reasons": r["attentionReasons"]} for r in att],
            "expiringList": [{"id": r["id"], "name": r["name"], "endDate": r["contractEndDate"], "daysRemaining": r["daysRemaining"]} for r in exp],
            "activity": {"active": len(rows), "total": len(rows), "windowDays": 30},
            "unreadNotifications": Notification.objects.filter(recipient=request.user, is_read=False).count(),
        })


class HomConsulsCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_hom_consul_rows(request.user))


class HomReportsCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reps = QuarterlyReport.objects.filter(consul__in=_scoped_consuls(request.user)).exclude(status="draft").order_by("-year", "-quarter")
        return Response([
            {
                "id": str(r.id),
                "consulId": str(r.consul.id),
                "consulName": r.consul.user.full_name,
                "quarter": _quarter_label(r.year, r.quarter),
                "submittedAt": r.submitted_at.strftime("%Y-%m-%d") if r.submitted_at else None,
                "reference": r.receipt_number or "-",
                "status": "pending_review" if r.status == "submitted" else "reviewed",
                "reviewedAt": r.reviewed_at.strftime("%Y-%m-%d") if r.reviewed_at else None,
                "comment": r.hom_remarks or "",
                "content": {
                    "summary": r.executive_summary or "",
                    "achievements": r.trade_and_investment or "",
                    "challenges": "",
                    "plans": r.diaspora_and_consular_services or "",
                    "attachments": [a.original_filename for a in r.attachments.all()],
                },
            }
            for r in reps
        ])


class HomReportReviewCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        r = QuarterlyReport.objects.filter(id=pk, consul__in=_scoped_consuls(request.user)).first()
        if not r:
            return Response(status=404)
        r.status = "endorsed"
        r.reviewed_by = request.user
        r.reviewed_at = timezone.now()
        r.hom_remarks = request.data.get("comment", "")
        r.save()
        return Response({"status": "reviewed"})


class HomPerformanceCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        out = []
        for c in _scoped_consuls(request.user):
            reps = list(QuarterlyReport.objects.filter(consul=c).order_by("-year", "-quarter"))
            evals = list(PerformanceEvaluation.objects.filter(consul=c).order_by("-year", "-quarter"))
            total_logs = WorkLogEntry.objects.filter(consul=c).count()
            last_log = WorkLogEntry.objects.filter(consul=c).order_by("-activity_date").first()
            out.append({
                "consulId": str(c.id),
                "name": c.user.full_name,
                "city": c.cities_of_operation or "-",
                "metrics": {
                    "reportsOnTime": len([r for r in reps if r.status in ("submitted", "endorsed")]),
                    "reportsTotal": max(len(reps), 1),
                    "avgEntriesPerQuarter": total_logs,
                    "lastActivity": str(last_log.activity_date) if last_log else None,
                },
                "quarters": [{"quarter": _quarter_label(r.year, r.quarter), "entries": total_logs, "reportStatus": r.status} for r in reps],
                "evaluations": [
                    {"id": str(e.id), "quarter": _quarter_label(e.year, e.quarter), "rating": e.overall_rating, "comment": e.comments, "date": e.created_at.strftime("%Y-%m-%d")}
                    for e in evals
                ],
            })
        return Response(out)


class HomEvaluationsCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        y, q = _parse_quarter(request.data.get("quarter"))
        consul_id = request.data.get("consulId")
        if PerformanceEvaluation.objects.filter(consul_id=consul_id, year=y, quarter=q).exists():
            return Response({"error": "Already evaluated for this quarter."}, status=409)
        rating = request.data.get("rating", "good")
        score = {"excellent": 5, "good": 4, "satisfactory": 3, "needs_improvement": 2}.get(rating, 4)
        ev = PerformanceEvaluation.objects.create(
            consul_id=consul_id, evaluator=request.user, year=y, quarter=q,
            overall_rating=rating, diplomatic_conduct=score, reporting_compliance=score,
            comments=request.data.get("comment", ""),
        )
        return Response({"id": str(ev.id)}, status=201)


class HomRecommendationsCompatView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = _hom_consul_rows(request.user)
        recs = list(Recommendation.objects.filter(consul__in=_scoped_consuls(request.user)).order_by("-created_at"))
        waiting_ids = {str(r.consul_id) for r in recs}
        needed = [
            {"consulId": r["id"], "name": r["name"], "city": r["city"], "contractEndDate": r["contractEndDate"], "daysRemaining": r["daysRemaining"], "latestRating": None}
            for r in rows if r["daysRemaining"] <= 180 and r["id"] not in waiting_ids
        ]
        submitted = []
        for r in recs:
            rc = RenewalCase.objects.filter(expiring_contract__consul=r.consul).first()
            st = "approved" if (rc and rc.status == "approved") else ("declined" if (rc and rc.status == "declined") else "submitted")
            submitted.append({
                "id": str(r.id), "consulId": str(r.consul_id), "consulName": r.consul.user.full_name,
                "recommendation": r.recommendation, "justification": r.justification,
                "submittedAt": r.created_at.strftime("%Y-%m-%d"), "status": st,
                "hqNote": rc.decision_notes if rc else "",
            })
        return Response({"needed": needed, "submitted": submitted})

    def post(self, request):
        rec = Recommendation.objects.create(
            consul_id=request.data.get("consulId"),
            recommended_by=request.user,
            recommendation=request.data.get("recommendation", "renew"),
            justification=request.data.get("justification", ""),
        )
        return Response({"id": str(rec.id)}, status=201)

