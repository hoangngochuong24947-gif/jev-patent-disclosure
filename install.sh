#!/usr/bin/env bash
# =============================================================================
# install.sh — One-Click Setup & Installer for jev-patent-disclosure
# =============================================================================
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}   jev-patent-disclosure — Automated Setup & Agent Mounting      ${NC}"
echo -e "${BLUE}=================================================================${NC}"

# 1. Check Python
echo -e "\n${YELLOW}[1/4] Checking Python environment...${NC}"
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Error: python3 is not installed or not in PATH.${NC}"
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "Found Python version: ${GREEN}${PY_VER}${NC}"

# 2. Install dependencies
echo -e "\n${YELLOW}[2/4] Installing patent suite dependencies...${NC}"
if [ "$1" == "--venv" ]; then
    if [ ! -d "${REPO_DIR}/.venv" ]; then
        echo "Creating virtual environment at .venv..."
        python3 -m venv "${REPO_DIR}/.venv"
    fi
    source "${REPO_DIR}/.venv/bin/activate"
    echo -e "Activated virtualenv: ${GREEN}${REPO_DIR}/.venv${NC}"
fi

python3 -m pip install -q -r "${REPO_DIR}/requirements.txt"
echo -e "${GREEN}✓ Dependencies installed successfully.${NC}"

# 3. Check OpenRouter API Key
echo -e "\n${YELLOW}[3/4] Checking Jev / OpenRouter configuration...${NC}"
if [ -n "$OPENROUTER_API_KEY" ]; then
    echo -e "${GREEN}✓ OPENROUTER_API_KEY is detected in environment.${NC}"
elif [ -f "${REPO_DIR}/.env" ] && grep -q "OPENROUTER_API_KEY=" "${REPO_DIR}/.env"; then
    echo -e "${GREEN}✓ OPENROUTER_API_KEY found in .env.${NC}"
elif command -v jev &>/dev/null; then
    echo -e "${GREEN}✓ Local 'jev' CLI binary found in PATH.${NC}"
else
    echo -e "${YELLOW}! Neither OPENROUTER_API_KEY nor 'jev' CLI was found.${NC}"
    echo -e "  To enable 300ms fast patent intake gate, please run:"
    echo -e "    ${BLUE}export OPENROUTER_API_KEY=\"sk-or-v1-...\"${NC}"
    echo -e "  Or add OPENROUTER_API_KEY=your_key to a .env file."
fi

# 4. Agent Platforms Integration
echo -e "\n${YELLOW}[4/4] Detecting AI Agent environments for skill mounting...${NC}"

AGENT_DIRS=(
    "$HOME/.claude/skills"
    "$HOME/.gemini/config/skills"
    "$HOME/.agents/skills"
    "$HOME/.cursor/skills"
)

MOUNTED=0
for AGENT_DIR in "${AGENT_DIRS[@]}"; do
    PARENT_DIR="$(dirname "$AGENT_DIR")"
    if [ -d "$PARENT_DIR" ]; then
        mkdir -p "$AGENT_DIR"
        TARGET_LINK="${AGENT_DIR}/patent-disclosure-skill"
        if [ ! -e "$TARGET_LINK" ]; then
            ln -s "$REPO_DIR" "$TARGET_LINK"
            echo -e "  ${GREEN}✓ Mounted skill into:${NC} $TARGET_LINK"
            MOUNTED=1
        else
            echo -e "  ${BLUE}• Already mounted at:${NC} $TARGET_LINK"
            MOUNTED=1
        fi
    fi
done

if [ $MOUNTED -eq 0 ]; then
    echo "  (No agent skill directories detected. Manual mounting available via README)"
fi

echo -e "\n${GREEN}=================================================================${NC}"
echo -e "${GREEN}   Installation Complete! Ready to audit and draft patents!     ${NC}"
echo -e "${GREEN}=================================================================${NC}"
echo -e "Quick Tests:"
echo -e "  1. Run comparison demo : ${BLUE}python3 examples/demo_jev_intake_comparison.py${NC}"
echo -e "  2. Run intake test     : ${BLUE}python3 skills/patent-disclosure/tools/patent_intake_gate.py --mock-brief${NC}"
