import unittest

from services.degree_plan_service import (
    _merge_completed_course_sources,
    _normalize_catalog_year_display,
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


if __name__ == "__main__":
    unittest.main()
