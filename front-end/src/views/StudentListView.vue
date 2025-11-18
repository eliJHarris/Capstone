<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h4 font-weight-bold mb-6">Student List</h1>

    <v-row dense>
      <v-col
        v-for="student in students"
        :key="student.id"
        cols="12"
        md="6"
        lg="4"
      >
        <v-card rounded="lg" elevation="4" class="pa-4">

         
          <div class="text-start mb-3">
            <div class="text-h6">{{ student.name }}</div>
            <div class="text-body-2 text-medium-emphasis">{{ student.major }}</div>
          </div>

          
          <div class="text-start mb-4">
            <v-chip
              v-if="student.approvedSchedule"
              size="small"
              class="ma-0"
              :style="{
                backgroundColor: '#c5e6cd',
                color: '#2e5f3d'
              }"
            >
              Approved for {{ currentSemester }}
            </v-chip>

            
            <v-chip
              v-else
              size="small"
              class="ma-0"
              :style="{
                backgroundColor: '#f4d6d6',
                color: '#7c3a3a'
              }"
            >
              Not Approved
            </v-chip>
          </div>

         
          <div class="d-flex align-center text-start mt-2" style="gap: 12px;">
            <v-btn
              variant="text"
              color="primary"
              size="small"
              class="px-0"
            >
              View Schedules
            </v-btn>

            <span class="text-medium-emphasis">·</span>

            <v-btn
              variant="text"
              color="secondary"
              size="small"
              class="px-0"
              :href="`mailto:${student.email}?subject=Appointment&body=Hello ${student.name}`"
            >
              Make Appointment
            </v-btn>
          </div>


        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>


<script setup>
import { ref } from "vue";

const currentSemester = "Spring 2025";

const students = ref([
  { id: 1, name: "Ethan Parks", major: "CS", email: "ethan@example.edu", approvedSchedule: true },
  { id: 2, name: "Maria Torres", major: "IT", email: "maria@example.edu", approvedSchedule: false },
  { id: 3, name: "James Caldwell", major: "Cybersecurity", email: "james@example.edu", approvedSchedule: false },
]);
</script>
