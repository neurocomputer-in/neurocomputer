#!/bin/bash
echo "Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh
echo "Starting Ollama service (if not already started)..."
sudo systemctl start ollama || true
echo "Pulling Gemma 2 27B model. This may take a few minutes depending on network speed..."
ollama pull gemma2:27b
echo "Pulling Gemma 2 9B model as a fallback..."
ollama pull gemma2:9b
echo "Done! You can run the model with: ollama run gemma2:27b"
