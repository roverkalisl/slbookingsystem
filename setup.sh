#!/bin/bash
# SL Booking - Development Setup Script

set -e

echo "================================"
echo "SL Booking - Development Setup"
echo "================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python
echo -e "${YELLOW}Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 not found. Please install Python 3.11 or higher.${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ Found: $PYTHON_VERSION${NC}"
echo ""

# Check PostgreSQL
echo -e "${YELLOW}Checking PostgreSQL installation...${NC}"
if ! command -v psql &> /dev/null; then
    echo -e "${RED}PostgreSQL not found. Please install PostgreSQL 14 or higher.${NC}"
    exit 1
fi
PG_VERSION=$(psql --version)
echo -e "${GREEN}✓ Found: $PG_VERSION${NC}"
echo ""

# Check Redis
echo -e "${YELLOW}Checking Redis installation...${NC}"
if ! command -v redis-cli &> /dev/null; then
    echo -e "${YELLOW}⚠ Redis not found. Some features may not work without Redis.${NC}"
else
    REDIS_VERSION=$(redis-cli --version)
    echo -e "${GREEN}✓ Found: $REDIS_VERSION${NC}"
fi
echo ""

# Create virtual environment
echo -e "${YELLOW}Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi
echo ""

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Create .env file if it doesn't exist
echo -e "${YELLOW}Checking .env file...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file (update with your settings)${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi
echo ""

# Create database
echo -e "${YELLOW}Creating PostgreSQL database...${NC}"
DB_NAME=${DB_NAME:-slbooking}
if psql -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo -e "${GREEN}✓ Database '$DB_NAME' already exists${NC}"
else
    createdb $DB_NAME
    echo -e "${GREEN}✓ Database '$DB_NAME' created${NC}"
fi
echo ""

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
cd backend
python manage.py migrate --settings=config.settings.development
echo -e "${GREEN}✓ Migrations complete${NC}"
echo ""

# Create superuser
echo -e "${YELLOW}Creating superuser...${NC}"
echo "Enter superuser details:"
python manage.py createsuperuser --settings=config.settings.development
echo ""

# Create logs directory
echo -e "${YELLOW}Creating logs directory...${NC}"
if [ ! -d "logs" ]; then
    mkdir logs
    echo -e "${GREEN}✓ Logs directory created${NC}"
else
    echo -e "${GREEN}✓ Logs directory already exists${NC}"
fi
echo ""

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Setup complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Next steps:"
echo "1. Update .env file with your settings"
echo "2. Start Django: python manage.py runserver --settings=config.settings.development"
echo "3. Visit: http://localhost:8000"
echo "4. Admin: http://localhost:8000/admin"
echo "5. API Docs: http://localhost:8000/api/docs/"
echo ""
