#!/bin/bash
# Sequential Conversation Test - Recency Bias Validation
# Tests if recent conversations are prioritized over semantically similar but older ones

echo "🧪 SEQUENTIAL CONVERSATION TEST"
echo "================================"
echo ""
echo "📋 Test Scenario:"
echo "1. Create chart conversation"
echo "2. Wait 3 seconds"
echo "3. Ask to modify chart (expect: chart context injected)"
echo ""

# Enable mock mode for faster testing
export LLM_MOCK=1

cd "$(dirname "$0")/.."

echo "Step 1: Creating chart conversation..."
echo "----------------------------------------"
.venv/bin/python scripts/agent_runner.py builder "Python'da matplotlib ile basit bar chart nasıl çizilir?"

echo ""
echo "⏳ Waiting 3 seconds..."
sleep 3

echo ""
echo "Step 2: Asking to modify chart..."
echo "----------------------------------------"
.venv/bin/python scripts/agent_runner.py builder "Önceki chart'a başlık ve renkler ekle"

echo ""
echo "📊 VERIFICATION:"
echo "----------------------------------------"

# Get last 2 conversations
LAST_TWO=$(ls -t data/CONVERSATIONS/*.json | head -2)

echo ""
echo "Last 2 conversations:"
echo ""

for file in $LAST_TWO; do
    echo "File: $(basename $file)"
    cat "$file" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"  Prompt: {data['prompt'][:60]}...\")
print(f\"  injected_context_tokens: {data.get('injected_context_tokens', 0)}\")
print()
"
done

echo "✅ EXPECTED RESULT:"
echo "   - First conversation: injected_context_tokens = 0"
echo "   - Second conversation: injected_context_tokens > 100 (chart context injected!)"
echo ""
echo "❌ OLD BEHAVIOR (before time_decay fix):"
echo "   - Both might be 0 or generic context (not chart-specific)"
echo ""
echo "🎯 SUCCESS CRITERIA:"
echo "   Second conversation should inject chart context due to recency bias!"
