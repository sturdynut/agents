#!/usr/bin/env python3
"""Check available Ollama models"""
import ollama

try:
    models = ollama.list()
    print("Available Ollama models:")
    print("-" * 40)
    
    if isinstance(models, dict) and 'models' in models:
        model_list = models['models']
    elif isinstance(models, list):
        model_list = models
    else:
        model_list = []
    
    if model_list:
        for m in model_list:
            if isinstance(m, dict):
                name = m.get('name', 'Unknown')
                size = m.get('size', 0)
                print(f"  ✓ {name} ({size / 1024 / 1024 / 1024:.2f} GB)" if size else f"  ✓ {name}")
            else:
                print(f"  ✓ {m}")
    else:
        print("  No models found. Download one with: ollama pull llama3.2")
        
except Exception as e:
    print(f"Error checking models: {e}")
    print("Make sure Ollama is running: ollama serve")

