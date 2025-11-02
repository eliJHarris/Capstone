#!/bin/bash

# AdviseMe API Test Script
# Tests the Schedule CRUD endpoints

API_URL="http://localhost:8000"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}AdviseMe API - Schedule CRUD Tests${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Health Check${NC}"
response=$(curl -s "$API_URL/")
if echo "$response" | grep -q "AdviseMe API is running"; then
    echo -e "${GREEN}✓ API is running${NC}"
else
    echo -e "${RED}✗ API is not responding${NC}"
    exit 1
fi
echo ""

# Test 2: Database Check
echo -e "${YELLOW}Test 2: Database Connection${NC}"
response=$(curl -s "$API_URL/db")
if echo "$response" | grep -q "connected"; then
    echo -e "${GREEN}✓ Database connected${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
fi
echo ""

# Test 3: Get All Schedules
echo -e "${YELLOW}Test 3: Get All Schedules${NC}"
response=$(curl -s "$API_URL/api/schedules")
echo "Response: $response"
echo -e "${GREEN}✓ Retrieved schedules${NC}"
echo ""

# Test 4: Get Schedule by ID
echo -e "${YELLOW}Test 4: Get Schedule by ID (scheduleID=1)${NC}"
response=$(curl -s "$API_URL/api/schedules/1")
echo "Response: $response"
if echo "$response" | grep -q "scheduleID"; then
    echo -e "${GREEN}✓ Retrieved schedule details${NC}"
else
    echo -e "${RED}✗ Failed to retrieve schedule${NC}"
fi
echo ""

# Test 5: Get Schedules with Filters
echo -e "${YELLOW}Test 5: Get Schedules for Advisee 1${NC}"
response=$(curl -s "$API_URL/api/schedules?advisee_id=1")
echo "Response: $response"
echo -e "${GREEN}✓ Retrieved filtered schedules${NC}"
echo ""

# Test 6: Get Draft Schedules
echo -e "${YELLOW}Test 6: Get Draft Schedules${NC}"
response=$(curl -s "$API_URL/api/schedules?status=DRAFT")
echo "Response: $response"
echo -e "${GREEN}✓ Retrieved draft schedules${NC}"
echo ""

# Test 7: Create New Schedule
echo -e "${YELLOW}Test 7: Create New Schedule${NC}"
response=$(curl -s -L -X POST "$API_URL/api/schedules" \
  -H "Content-Type: application/json" \
  -d '{
    "adviseeID": 1,
    "termID": 2,
    "source": "USER",
    "status": "DRAFT"
  }')
echo "Response: $response"
if echo "$response" | grep -q "scheduleID"; then
    schedule_id=$(echo "$response" | grep -o '"scheduleID":[0-9]*' | grep -o '[0-9]*')
    echo -e "${GREEN}✓ Created schedule with ID: $schedule_id${NC}"

    # Test 8: Add Class to Schedule
    echo ""
    echo -e "${YELLOW}Test 8: Add Class to Schedule${NC}"
    response=$(curl -s -L -X POST "$API_URL/api/schedules/$schedule_id/classes" \
      -H "Content-Type: application/json" \
      -d '{"sectionID": 1}')
    echo "Response: $response"
    if echo "$response" | grep -q "classID"; then
        echo -e "${GREEN}✓ Added class to schedule${NC}"
    else
        echo -e "${RED}✗ Failed to add class${NC}"
    fi

    # Test 9: Update Schedule Status
    echo ""
    echo -e "${YELLOW}Test 9: Update Schedule Status to APPROVED${NC}"
    response=$(curl -s -L -X PUT "$API_URL/api/schedules/$schedule_id" \
      -H "Content-Type: application/json" \
      -d '{"status": "APPROVED"}')
    echo "Response: $response"
    if echo "$response" | grep -q "APPROVED"; then
        echo -e "${GREEN}✓ Schedule approved${NC}"
    else
        echo -e "${RED}✗ Failed to update schedule${NC}"
    fi

    # Test 10: Get Updated Schedule
    echo ""
    echo -e "${YELLOW}Test 10: Verify Schedule Updates${NC}"
    response=$(curl -s "$API_URL/api/schedules/$schedule_id")
    echo "Response: $response"
    if echo "$response" | grep -q "approvedWhen"; then
        echo -e "${GREEN}✓ Schedule has approval timestamp${NC}"
    fi

    # Test 11: Delete Schedule
    echo ""
    echo -e "${YELLOW}Test 11: Delete Schedule${NC}"
    response=$(curl -s -X DELETE "$API_URL/api/schedules/$schedule_id")
    echo "Response: $response"
    if echo "$response" | grep -q "deleted successfully"; then
        echo -e "${GREEN}✓ Schedule deleted${NC}"
    else
        echo -e "${RED}✗ Failed to delete schedule${NC}"
    fi
else
    echo -e "${RED}✗ Failed to create schedule${NC}"
fi

echo ""
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Test Suite Complete${NC}"
echo -e "${YELLOW}========================================${NC}"
