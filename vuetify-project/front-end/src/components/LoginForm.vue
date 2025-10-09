<template>
  <div class="login-container">
    <div class="login-card">
      <h2 class="login-title">Welcome Back</h2>
      <form @submit.prevent="login" class="login-form">
        <APIButton/>
        <div class="form-group">
          <label for="user">User Type</label>
          <select v-model="userType" id="user">
            <option value="student">Student</option>
            <option value="advisor">Advisor</option>
          </select>
        </div>
        <div class="form-group">
          <label for="username">Username</label>
          <input type="text" id="username" v-model="username" placeholder="Enter username" />
        </div>
        <div class="form-group">
          <label for="password">Password</label>
          <input type="password" id="password" v-model="password" placeholder="Enter password" />
        </div>
        <button type="submit" class="login-button">Login</button>
      </form>
    </div>
  </div>
</template>

<script>
import { useUserStore } from '@/stores/user';
import APIButton from './APIButton.vue';

export default {
  name: 'LoginForm',
  data() {
    return {
      userType: 'student',
      username: '',
      password: '',
    }
  },
  setup() {
    const userStore = useUserStore()
    return { userStore }
  },
  methods: {
    login() {
      // Simple mock login for now
      if (this.username && this.password) {
        this.userStore.login(this.userType)
        alert(`Logged in as ${this.userType}`)
      } else {
        alert('Please enter username and password')
      }
    },
  },
}
</script>

<style scoped>
/* Center everything vertically & horizontally */
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(135deg, #6b73ff, #000dff);
  font-family: Arial, sans-serif;
}

/* Card */
.login-card {
  background: white;
  padding: 2rem 2.5rem;
  border-radius: 10px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  width: 320px;
  text-align: center;
}

/* Title */
.login-title {
  margin-bottom: 1.5rem;
  color: #333;
}

/* Form */
.login-form .form-group {
  margin-bottom: 1rem;
  text-align: left;
}

.login-form label {
  display: block;
  margin-bottom: 0.25rem;
  color: #555;
  font-weight: 500;
}

.login-form input,
.login-form select {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border-radius: 5px;
  border: 1px solid #ccc;
  outline: none;
  transition: border 0.2s ease-in-out;
}

.login-form input:focus,
.login-form select:focus {
  border-color: #6b73ff;
}

/* Button */
.login-button {
  width: 100%;
  padding: 0.6rem;
  background: #6b73ff;
  color: white;
  border: none;
  border-radius: 5px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.3s ease-in-out;
}

.login-button:hover {
  background: #000dff;
}
</style>
