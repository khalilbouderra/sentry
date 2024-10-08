from django.core.files.base import ContentFile

from sentry.db.postgres.transactions import in_test_hide_transaction_boundary
from sentry.models.files import File
from sentry.monitors.models import CheckInStatus, MonitorCheckIn
from sentry.testutils.cases import MonitorTestCase


class BaseMonitorCheckInAttachmentEndpointTest(MonitorTestCase):
    __test__ = False

    def setUp(self):
        super().setUp()
        self.login_as(self.user)

    def test_download(self):
        file = self.create_file(name="log.txt", type="checkin.attachment")
        file.putfile(ContentFile(b"some data!"))

        monitor = self._create_monitor()
        monitor_environment = self._create_monitor_environment(monitor)
        checkin = MonitorCheckIn.objects.create(
            monitor=monitor,
            monitor_environment=monitor_environment,
            project_id=self.project.id,
            date_added=monitor.date_added,
            status=CheckInStatus.IN_PROGRESS,
            attachment_id=file.id,
        )

        resp = self.get_success_response(self.organization.slug, monitor.slug, checkin.guid)
        assert resp.get("Content-Disposition") == "attachment; filename=log.txt"
        assert b"".join(resp.streaming_content) == b"some data!"

    def test_download_no_file(self):
        monitor = self._create_monitor()
        monitor_environment = self._create_monitor_environment(monitor)
        checkin = MonitorCheckIn.objects.create(
            monitor=monitor,
            monitor_environment=monitor_environment,
            project_id=self.project.id,
            date_added=monitor.date_added,
            status=CheckInStatus.IN_PROGRESS,
        )

        resp = self.get_error_response(
            self.organization.slug, monitor.slug, checkin.guid, status_code=404
        )
        assert resp.data["detail"] == "Check-in has no attachment"

    def test_delete_cascade(self):
        file = self.create_file(name="log.txt", type="checkin.attachment")
        file.putfile(ContentFile(b"some data!"))

        monitor = self._create_monitor()
        monitor_environment = self._create_monitor_environment(monitor)
        checkin = MonitorCheckIn.objects.create(
            monitor=monitor,
            monitor_environment=monitor_environment,
            project_id=self.project.id,
            date_added=monitor.date_added,
            status=CheckInStatus.IN_PROGRESS,
            attachment_id=file.id,
        )

        # checkin has a post_delete signal that removes files.
        with in_test_hide_transaction_boundary():
            checkin.delete()

        assert not File.objects.filter(type="checkin.attachment").exists()
