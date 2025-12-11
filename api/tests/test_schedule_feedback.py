from datetime import datetime, timedelta
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.base import Base
from models.schedule import Term
from schemas.schedule import ScheduleCreate, ScheduleSource, ScheduleStatus, ScheduleUpdate
from services.schedule_service import ScheduleService


class ScheduleFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        term = Term(
            code="2025FA",
            startDate=datetime.utcnow(),
            endDate=datetime.utcnow() + timedelta(days=90),
        )
        self.session.add(term)
        self.session.commit()
        self.term_id = term.termID

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _create_schedule(self, advisor_feedback=None):
        payload = ScheduleCreate(
            adviseeID=1,
            termID=self.term_id,
            source=ScheduleSource.ADVISOR,
            status=ScheduleStatus.DRAFT,
            advisorFeedback=advisor_feedback,
        )
        return ScheduleService.create_schedule(self.session, payload)

    def test_create_schedule_persists_advisor_feedback(self):
        response = self._create_schedule(advisor_feedback="Complete math prereq first")

        self.assertEqual(response.advisorFeedback, "Complete math prereq first")

        fetched = ScheduleService.get_schedule_by_id(self.session, response.scheduleID)
        self.assertEqual(fetched.advisorFeedback, "Complete math prereq first")

    def test_update_schedule_feedback_can_be_trimmed_and_cleared(self):
        response = self._create_schedule()

        updated = ScheduleService.update_schedule(
            self.session,
            response.scheduleID,
            ScheduleUpdate(advisorFeedback="  Need advisor approval  "),
        )
        self.assertEqual(updated.advisorFeedback, "Need advisor approval")

        cleared = ScheduleService.update_schedule(
            self.session,
            response.scheduleID,
            ScheduleUpdate(advisorFeedback="   "),
        )
        self.assertIsNone(cleared.advisorFeedback)


if __name__ == "__main__":
    unittest.main()
