import { ref, computed } from 'vue'
import { fetchAdvisees } from '@/services/advisees'
import { fetchUserByUsername } from '@/services/users'
import { normalizeRole, resolveStoredIdentity, NORMALIZED_ROLES } from '@/utils/auth'
import { useStudentProfileStore } from '@/stores/studentProfile'

const identityRef = ref(resolveStoredIdentity())
const userRef = ref(null)
const adviseeRef = ref(null)
const loading = ref(false)
const error = ref(null)

const role = computed(() =>
  normalizeRole(userRef.value?.role || identityRef.value?.role, NORMALIZED_ROLES.STUDENT)
)

const username = computed(() => userRef.value?.username || identityRef.value?.username || '')
const email = computed(() => userRef.value?.email || identityRef.value?.email || '')
const displayName = computed(
  () => identityRef.value?.displayName || userRef.value?.username || username.value
)

export function useCurrentUser() {
  const studentProfileStore = useStudentProfileStore()
  const refreshIdentity = () => {
    identityRef.value = resolveStoredIdentity(role.value)
  }

  const loadUserContext = async () => {
    loading.value = true
    error.value = null

    try {
      const baseIdentity = resolveStoredIdentity()
      identityRef.value = baseIdentity

      if (!baseIdentity?.username) {
        throw new Error('Missing username in auth data')
      }

      const userRecord = await fetchUserByUsername(baseIdentity.username)
      const normalizedRole = normalizeRole(userRecord?.role || baseIdentity.role)

      if (!userRecord && normalizedRole === NORMALIZED_ROLES.STUDENT) {
        throw new Error(`No user record found for ${baseIdentity.username}`)
      }

      userRef.value = userRecord

      if (normalizedRole === NORMALIZED_ROLES.STUDENT) {
        const advisees = await fetchAdvisees({ userId: userRecord?.userID, limit: 1 })
        adviseeRef.value = Array.isArray(advisees) && advisees.length ? advisees[0] : null
        if (!adviseeRef.value) {
          throw new Error('No advisee profile found for this account')
        }
        await studentProfileStore.loadDashboard({
          advisee: adviseeRef.value,
          user: userRecord,
          identity: identityRef.value,
        })
      } else {
        adviseeRef.value = null
        studentProfileStore.reset()
      }
    } catch (err) {
      console.error(err)
      error.value = err.message || 'Failed to load user context'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    role,
    username,
    email,
    displayName,
    identity: identityRef,
    user: userRef,
    advisee: adviseeRef,
    loading,
    error,
    refreshIdentity,
    loadUserContext,
  }
}
