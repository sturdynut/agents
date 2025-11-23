# Quick Start: Semantic Knowledge Base

## 🎯 What Changed?

Your agent system now uses **semantic search** to retrieve relevant knowledge instead of just loading recent history. This makes it smarter, more efficient, and scalable.

---

## 🚀 Quick Setup (3 Steps)

### Step 1: Install Embedding Model

```bash
# Make sure Ollama is running
ollama serve

# Install the embedding model (one-time, ~270MB)
ollama pull nomic-embed-text
```

### Step 2: Migrate Existing Data (Optional)

If you have existing interactions in your knowledge base:

```bash
python3 migrate_embeddings.py
```

This generates embeddings for all existing interactions (~2 sec per 100 interactions).

### Step 3: Done! 

Your agents now automatically use semantic search. No code changes needed!

---

## ✅ Verify It's Working

```bash
# Run the test suite
python3 test_semantic_search.py

# See the comparison between old and new
python3 test_semantic_search.py --compare
```

---

## 📚 How It Works Now

### Before (Old Way)
```
User: "How do I optimize performance?"

Agent retrieves:
  - Last 20 interactions (chronological)
  - Might include irrelevant topics
  - Same context for every query
```

### After (New Way)
```
User: "How do I optimize performance?"

Agent retrieves:
  - Top 10 most relevant interactions about performance
  - Weighted by recency (recent + relevant = best)
  - Context adapts to each specific query
```

---

## 💡 Examples

### Example 1: Agent Chat

```python
from agent_core import EnhancedAgent
from knowledge_base import KnowledgeBase

kb = KnowledgeBase()
agent = EnhancedAgent(name="helper", model="llama3.2", knowledge_base=kb)

# Chat about databases
agent.chat("How do I connect to PostgreSQL?")

# Chat about APIs
agent.chat("How do I make a REST API call?")

# Chat about databases again
# Agent retrieves the PostgreSQL conversation automatically!
agent.chat("How do I query the database?")
```

### Example 2: Programmatic Search

```python
from knowledge_base import KnowledgeBase

kb = KnowledgeBase()

# Search for relevant interactions
results = kb.semantic_search_interactions(
    query="database configuration",
    agent_name="my_agent",
    top_k=5
)

for r in results:
    print(f"Score: {r['relevance_score']:.2f} - {r['content'][:100]}")
```

---

## 🎛️ Configuration

Edit `config.yaml` to customize:

```yaml
embeddings:
  model: "nomic-embed-text"        # Embedding model
  top_k: 10                        # Number of results
  time_decay_factor: 0.95          # Recency weight (higher = less decay)
  cache_size: 1000                 # Embedding cache size
```

**Tuning Tips:**
- **More top_k** = more context but slower LLM calls
- **Higher decay_factor** (0.98) = prioritize relevance over recency
- **Lower decay_factor** (0.90) = prioritize recent interactions

---

## 🔧 Troubleshooting

### Problem: Ollama errors

```bash
# Make sure Ollama is running
ollama serve

# Verify model is installed
ollama list | grep nomic-embed-text

# If not found, install it
ollama pull nomic-embed-text
```

### Problem: Embeddings not generated

Check the logs for `[EmbeddingService]` messages. The system has fallback logic, so it will continue working even without embeddings (using chronological approach).

### Problem: Results not relevant

1. Increase `top_k` to 15-20
2. Adjust `time_decay_factor` to 0.98 (more relevance weight)
3. Run migration to ensure all interactions have embeddings

---

## 📖 Full Documentation

For detailed information:
- **Setup & Usage:** `SEMANTIC_KNOWLEDGE_BASE.md`
- **Implementation Details:** `IMPLEMENTATION_SUMMARY.md`
- **Test Coverage:** Run `python3 test_semantic_search.py`

---

## 🎉 That's It!

Your knowledge base is now semantic and will automatically:
✅ Retrieve relevant context for each query  
✅ Balance recency with relevance  
✅ Scale as your knowledge base grows  
✅ Reduce token usage in LLM calls  

**No code changes needed in your existing agents!** They automatically benefit from semantic search.

---

## 🤔 Questions?

- **How it works?** See `SEMANTIC_KNOWLEDGE_BASE.md`
- **Migrate existing data?** Run `python3 migrate_embeddings.py`
- **Test the system?** Run `python3 test_semantic_search.py`
- **Configuration?** Edit `config.yaml` embeddings section

