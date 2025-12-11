import unittest

from services.degree_plan_service import (
    _merge_completed_course_sources,
    _normalize_catalog_year_display,
    DegreePlanService,
)


class CompletedCourseMergeTests(unittest.TestCase):
    def test_merge_includes_context_courses_when_transcript_missing_entries(self):
        transcript = [
            {"code": "CS 1013", "credits": 3, "term": "Fall 2023", "status": "COMPLETED"},
        ]
        imported = [
            {"code": "CS 1013", "credits": 3, "term": "Fall 2023", "status": "COMPLETED"},
            {"code": "MATH 2804", "credits": 4, "term": "Spring 2023", "status": "COMPLETED"},
        ]

        merged = _merge_completed_course_sources(transcript, imported)

        self.assertEqual(len(merged), 2)
        codes = {entry["code"] for entry in merged}
        self.assertIn("CS 1013", codes)
        self.assertIn("MATH 2804", codes)

    def test_merge_deduplicates_by_code_term_and_title(self):
        duplicate_context = [
            {"code": "ENG 1013", "credits": 3, "term": "Fall 2022", "title": "Composition I", "status": "COMPLETED"},
            {"code": "ENG 1013", "credits": 3, "term": "Fall 2022", "title": "Composition I", "status": "COMPLETED"},
        ]

        merged = _merge_completed_course_sources([], duplicate_context)

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["code"], "ENG 1013")
        self.assertEqual(merged[0]["credits"], 3.0)

    def test_merge_ignores_planned_courses(self):
        transcript = [{"code": "CS 1013", "credits": 3, "term": "FA23", "status": "COMPLETED"}]
        imported = [
            {"code": "MATH 2804", "credits": 4, "term": "FA23", "status": "PLANNED"},
            {"code": "MATH 2804", "credits": 4, "term": "FA23", "status": "COMPLETED"},
        ]

        merged = _merge_completed_course_sources(transcript, imported)

        codes = {entry["code"] for entry in merged}
        self.assertIn("CS 1013", codes)
        self.assertIn("MATH 2804", codes)
        self.assertEqual(len(codes), 2)

    def test_merge_skips_entries_that_are_only_planned(self):
        planned_only = [
            {"code": "ENG 2013", "credits": 3, "term": "SP24", "status": "PLANNED"},
        ]

        merged = _merge_completed_course_sources(planned_only)

        self.assertEqual(len(merged), 0)

    def test_catalog_year_display_strips_advisee_scope(self):
        self.assertEqual(
            _normalize_catalog_year_display("2024-2025::ADV-123"),
            "2024-2025",
        )
        self.assertEqual(
            _normalize_catalog_year_display("CAT2025"),
            "CAT2025",
        )


class PlacementCoRequisiteTests(unittest.TestCase):
    def test_collects_all_co_requisite_codes(self):
        payload = [
            {"title": "General Education", "courses": []},
            {
                "co_requisites_if_placement_not_met": {
                    "ENGL": ["ENGL 0201", "ENGL 0202"],
                    "MATH": ["MATH 0301", None, "MATH 0201"],
                }
            },
        ]

        codes = DegreePlanService._collect_assumed_corequisites(payload)
        self.assertSetEqual({"ENGL 0201", "ENGL 0202", "MATH 0301", "MATH 0201"}, codes)


class PrerequisiteWarningTests(unittest.TestCase):
    def test_warning_emitted_when_prerequisite_missing(self):
        course = {
            "code": "CS 2023",
            "prerequisites": [
                {
                    "type": "PREREQUISITE",
                    "options": [["CS 1013"], ["MATH 1403"]],
                    "text": "Prerequisite: CS 1013 or MATH 1403",
                }
            ],
        }
        completed = {"MATH 1403"}

        warnings = DegreePlanService._evaluate_course_prerequisites(course, completed)

        self.assertEqual(len(warnings), 1)
        self.assertIn("WARNING", warnings[0]["severity"])
        self.assertEqual(warnings[0]["missingCourses"], ["CS 1013", "MATH 1403"])

    def test_no_warning_when_prerequisite_satisfied(self):
        course = {
            "code": "CS 2023",
            "prerequisites": [
                {
                    "type": "PREREQUISITE",
                    "options": [["CS 1013"]],
                }
            ],
        }
        completed = {"CS 1013"}

        warnings = DegreePlanService._evaluate_course_prerequisites(course, completed)
        self.assertEqual(warnings, [])

    def test_corequisites_assumed_completed(self):
        course = {
            "code": "CS 3033",
            "prerequisites": [
                {
                    "type": "corequisite",
                    "options": [["PHYS 1113"], ["MATH 2003"]],
                }
            ],
        }

        warnings = DegreePlanService._evaluate_course_prerequisites(course, set())
        self.assertEqual(warnings, [])

    def test_prereq_or_concurrent_also_assumed_completed(self):
        course = {
            "code": "CS 3043",
            "prerequisites": [
                {
                    "type": "PREREQ_OR_CONCURRENT",
                    "options": [["ENGR 2003"]],
                }
            ],
        }

        warnings = DegreePlanService._evaluate_course_prerequisites(course, set())
        self.assertEqual(warnings, [])


class GeneralEducationSummaryTests(unittest.TestCase):
    def test_general_education_summary_tracks_taken_and_remaining(self):
        group = {
            "id": "gen-ed-lab-science",
            "title": "General Education Core Lab Science",
            "description": "Select two from the following lab science options.",
            "courses": [
                {"code": "GEOL 1253", "title": "Physical Geology"},
                {"code": "CHEM 1403", "title": "College Chemistry I"},
                {"code": "PHYS 2903", "title": "University Physics I"},
            ],
        }

        summary, required_total, satisfied_total = DegreePlanService._build_general_education_summary(
            [group],
            {"GEOL 1253", "CHEM 1403"},
        )

        self.assertEqual(required_total, 2)
        self.assertEqual(satisfied_total, 2)
        self.assertEqual(len(summary), 1)
        entry = summary[0]
        self.assertEqual(entry["requiredSelections"], 2)
        self.assertEqual(entry["satisfiedSelections"], 2)
        self.assertEqual(entry["remainingSelections"], 0)
        self.assertListEqual(
            entry["takenCourses"],
            [
                "GEOL 1253 - Physical Geology",
                "CHEM 1403 - College Chemistry I",
            ],
        )
        self.assertIn("PHYS 2903 - University Physics I", entry["remainingCourses"])


if __name__ == "__main__":
    unittest.main()
