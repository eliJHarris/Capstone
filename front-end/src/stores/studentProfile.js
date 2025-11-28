import { defineStore } from 'pinia'

/**
 * Centralized store for the currently selected student profile.
 * Additional components can import this store to share and update profile data.
 */
export const useStudentProfileStore = defineStore('studentProfile', {
  state: () => ({
    profile: {
      student_name: 'Jordan Casey',
      major: 'B.S. Computer Science',
      advisee_id: 1001,
      catalog_year: 'CAT2024',
      program_code: 'BS-CS',
      advisor_name: 'Dr. Samantha Lee',
      holds_list: ['Advising Hold - Meet with advisor before registration'],
      degree_plan_summary:
        'Completed 78/120 credit hours. Remaining pathway includes Capstone, two upper-level CS electives, and ENG 4883.',
      policies_summary:
        'Students must maintain a 2.0 GPA, earn at least 30 upper-level credit hours, and clear all holds before enrollment each term.',
    },
  }),
  getters: {
    studentProfile: (state) => state.profile,
  },
  actions: {
    updateProfile(updates = {}) {
      this.profile = {
        ...this.profile,
        ...updates,
      }
    },
    replaceProfile(newProfile = {}) {
      this.profile = {
        ...newProfile,
      }
    },
  },
})
