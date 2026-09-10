#!/bin/bash
# Test runner script for SL Booking backend

set -e

echo "🧪 SL Booking - Test Suite Runner"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Django is installed
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python not found${NC}"
    exit 1
fi

# Default arguments
TEST_FILTER=${1:-""}
VERBOSITY=${2:-"2"}
WITH_COVERAGE=${3:-"false"}

# Run tests based on argument
if [ "$TEST_FILTER" == "all" ] || [ -z "$TEST_FILTER" ]; then
    echo -e "${YELLOW}Running all tests...${NC}"
    python manage.py test apps.core apps.properties apps.bookings apps.payments apps.notifications --verbosity=$VERBOSITY
elif [ "$TEST_FILTER" == "core" ]; then
    echo -e "${YELLOW}Running Phase 1 tests (Authentication)...${NC}"
    python manage.py test apps.core --verbosity=$VERBOSITY
elif [ "$TEST_FILTER" == "properties" ]; then
    echo -e "${YELLOW}Running Phase 2 tests (Property Management)...${NC}"
    python manage.py test apps.properties --verbosity=$VERBOSITY
elif [ "$TEST_FILTER" == "bookings" ]; then
    echo -e "${YELLOW}Running Phase 3 tests (Booking Engine)...${NC}"
    python manage.py test apps.bookings --verbosity=$VERBOSITY
elif [ "$TEST_FILTER" == "payments" ]; then
    echo -e "${YELLOW}Running Phase 4 tests (Payments)...${NC}"
    python manage.py test apps.payments --verbosity=$VERBOSITY
elif [ "$TEST_FILTER" == "notifications" ]; then
    echo -e "${YELLOW}Running Phase 5 tests (Notifications)...${NC}"
    python manage.py test apps.notifications --verbosity=$VERBOSITY
elif [ "$TEST_FILTER" == "critical" ]; then
    echo -e "${YELLOW}Running critical tests only...${NC}"
    python manage.py test apps.bookings.tests.ConcurrentBookingTestCase --verbosity=$VERBOSITY
    python manage.py test apps.bookings.tests.BookingServiceTestCase.test_double_booking_prevention --verbosity=$VERBOSITY
else
    echo -e "${YELLOW}Running specific test: $TEST_FILTER${NC}"
    python manage.py test "$TEST_FILTER" --verbosity=$VERBOSITY
fi

# Run coverage if requested
if [ "$WITH_COVERAGE" == "true" ]; then
    echo ""
    echo -e "${YELLOW}Generating coverage report...${NC}"
    coverage run --source='.' manage.py test
    coverage report
    coverage html
    echo -e "${GREEN}✅ Coverage report generated (htmlcov/index.html)${NC}"
fi

echo ""
echo -e "${GREEN}✅ Tests completed!${NC}"
