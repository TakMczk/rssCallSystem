#!/usr/bin/env bash
cd /Users/rucaye/Documents/Code/rssCallSystem

echo "Testing batch processing with Gemini API..."
echo "Current configuration:"
echo "  USE_BATCH_SCORING: $(grep USE_BATCH_SCORING src/config.py | head -1)"
echo "  BATCH_SIZE: $(grep BATCH_SIZE src/config.py | head -1)"
echo "  USE_OPENAI: $(grep USE_OPENAI src/config.py | head -1)"
echo ""

python test_batch.py
