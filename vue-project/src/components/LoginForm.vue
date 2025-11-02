<template>
  <div class="login-container">
    <div class="login-card">
      <h2 class="login-title">Welcome Back</h2>

      <form @submit.prevent="login" class="login-form">
        <div class="form-group">
          <label for="user">User Type</label>
          <select v-model="userType" id="user">
            <option value="student">Student</option>
            <option value="advisor">Advisor</option>
          </select>
        </div>

        <div class="form-group">
          <label for="username">Username</label>
          <input id="username" v-model.trim="username" placeholder="Enter username" />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input id="password" type="password" v-model="password" placeholder="Enter password" />
        </div>

        <button type="submit" class="login-button" :disabled="loading">
          {{ loading ? 'Signing in…' : 'Login' }}
        </button>

        <p v-if="error" style="margin-top:.75rem;color:#b00020;background:#ffebee;padding:.5rem;border-radius:6px">
          {{ error }}
        </p>
      </form>
    </div>
  </div>
</template>

<script>
import { useUserStore } from '../store'

export default {
  name: 'LoginForm',
  data() {
    return {
      userType: 'student',
      username: '',
      password: '',
      loading: false,
      error: ''
    }
  },
  computed: {
    AUTH_BASE() { return import.meta.env.VITE_AUTH_API_BASE || 'http://localhost:8080' },
    CORE_BASE() { return import.meta.env.VITE_CORE_API_BASE || 'http://localhost:8081' }
  },
  created() {
    this.userStore = useUserStore()
  },
  methods: {
    async login() {
      this.error = ''
      if (!this.username || !this.password) {
        this.error = 'Please enter username and password'
        return
      }

      this.loading = true
      try {
        // FastAPI /login expects x-www-form-urlencoded
        const body = new URLSearchParams()
        body.set('username', this.username)   // If your API binds with cn=..., use "Alice Advisor"
        body.set('password', this.password)   // If you switched to uid=..., you can use "aadvisor"

        const resp = await fetch(`${this.AUTH_BASE}/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body
        })

        if (!resp.ok) {
          const msg = await resp.text()
          throw new Error(msg || `Login failed (${resp.status})`)
        }

        const data = await resp.json()
        const token = data.access_token
        if (!token) throw new Error('No token returned from auth API')

        // Save to Pinia
        this.userStore.setRole(this.userType)
        this.userStore.setToken(token)

        // Optional: pull claims from Core (/me)
        const me = await fetch(`${this.CORE_BASE}/me`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (me.ok) {
          const payload = await me.json()
          this.userStore.setClaims(payload.user || payload)
        }

        // Go to protected page
        this.$router.push('/test')
      } catch (e) {
        console.error(e)
        this.userStore.logout()
        this.error = 'Invalid credentials or server unavailable'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
/* your styles unchanged */
.login-container { display:flex; justify-content:center; align-items:center; height:100vh; background:linear-gradient(135deg,#6b73ff,#000dff); font-family:Arial,sans-serif }
.login-card { background:white; padding:2rem 2.5rem; border-radius:10px; box-shadow:0 10px 25px rgba(0,0,0,.2); width:320px; text-align:center }
.login-title { margin-bottom:1.5rem; color:#333 }
.login-form .form-group { margin-bottom:1rem; text-align:left }
.login-form label { display:block; margin-bottom:.25rem; color:#555; font-weight:500 }
.login-form input, .login-form select { width:100%; padding:.5rem .75rem; border-radius:5px; border:1px solid #ccc; outline:none; transition:border .2s }
.login-form input:focus, .login-form select:focus { border-color:#6b73ff }
.login-button { width:100%; padding:.6rem; background:#6b73ff; color:#fff; border:none; border-radius:5px; font-size:1rem; cursor:pointer; transition:background .3s }
.login-button:hover { background:#000dff }
</style>
