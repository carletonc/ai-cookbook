#!/bin/zsh
set -e

echo "Testing agent app..."
cd src/agent
pip install -r requirements.txt
streamlit run app.py --server.headless true --server.port 8501 &
AGENT_PID=$!
sleep 10
kill $AGENT_PID
cd ../..

echo "Testing mtg_recommender app..."
cd src/mtg_recommender
pip install -r requirements.txt
streamlit run app.py --server.headless true --server.port 8502 &
MTG_PID=$!
sleep 10
kill $MTG_PID
cd ../..

echo "Testing prompt_tuning app..."
cd src/prompt_tuning
pip install -r requirements.txt
streamlit run app.py --server.headless true --server.port 8503 &
PROMPT_PID=$!
sleep 10
kill $PROMPT_PID
cd ../..

echo "All apps tested."