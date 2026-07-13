#!/bin/bash

# Ensure we are inside a git repository
if [ ! -d .git ]; then
    echo "❌ Error: Please run this script from the root of your schema_merger_splitter repository."
    exit 1
fi

echo "================================================================="
echo "🔍 RUNNING SCHEMA-MERGER-SPLITTER DIAGNOSTIC SUITE"
echo "================================================================="

# 1. Check Local Tags
echo -e "\n1. Checking local git tags for 'model_5'..."
LOCAL_TAG=$(git tag -l "model_5")
if [ -n "$LOCAL_TAG" ]; then
    LOCAL_SHA=$(git rev-parse -q "$LOCAL_TAG")
    echo "✅ Local tag 'model_5' EXISTS (Points to commit: $LOCAL_SHA)"
else
    echo "❌ Local tag 'model_5' DOES NOT exist locally."
fi

# 2. Check Remote Tags on GitHub
echo -e "\n2. Fetching and checking remote tags on origin..."
git fetch --tags --quiet
REMOTE_TAG=$(git ls-remote --tags origin | grep "refs/tags/model_5")
if [ -n "$REMOTE_TAG" ]; then
    echo "✅ Remote tag 'model_5' EXISTS on GitHub repository:"
    echo "   $REMOTE_TAG"
else
    echo "❌ Remote tag 'model_5' DOES NOT exist on GitHub remote (origin)."
    echo "   (The orchestrator cannot pull it if it isn't on GitHub!)"
fi

# 3. Check tracking alignment
echo -e "\n3. Verifying local branch synchronization..."
git status -vv | grep -E "branch is|up to date" || echo "Working directory status verified."

# 4. Attempt to locate and parse Aggregator state.json
echo -e "\n4. Scanning for orchestrator state file (state.json)..."
# Common paths relative to a typical workspace structure
POSSIBLE_STATE_PATHS=(
    "../simulators_aggregator/data/testing-input-output/tuning_main/state.json"
    "../../simulators_aggregator/data/testing-input-output/tuning_main/state.json"
    "../data/testing-input-output/tuning_main/state.json"
)

STATE_FILE_FOUND=""
for path in "${POSSIBLE_STATE_PATHS[@]}"; do
    if [ -f "$path" ]; then
        STATE_FILE_FOUND="$path"
        break
    fi
done

if [ -n "$STATE_FILE_FOUND" ]; then
    echo "✅ Found state.json at: $STATE_FILE_FOUND"
    echo "   Targeted task configurations inside this file:"
    # Grep context around schema_merger_splitter or look for tags/versions
    if command -v jq &> /dev/null; then
        echo "--- Active Task Details ---"
        jq '.task_details[]? | select(.repository? | contains("schema_merger_splitter"))' "$STATE_FILE_FOUND" 2>/dev/null || grep -C 3 "schema_merger_splitter" "$STATE_FILE_FOUND"
    else
        grep -C 4 "schema_merger_splitter" "$STATE_FILE_FOUND"
    fi
else
    echo "⚠️  Could not find 'state.json' in nearby sibling directories."
    echo "   Please check the 'data/testing-input-output/tuning_main/state.json' file"
    echo "   inside your orchestrator/aggregator repository manually."
fi

echo -e "\n================================================================="
echo "📋 DIAGNOSTIC COMPLETE"
echo "================================================================="