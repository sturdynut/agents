# Semantic Knowledge Base

## Overview

The knowledge base now uses **semantic search with time-weighted scoring** to retrieve only relevant interactions instead of loading all recent history. This makes the system scalable, efficient, and context-aware.

## Key Improvements

### Before
- Retrieved last N interactions (e.g., 20) regardless of relevance
- No filtering based on current task/query
- Knowledge base would become overwhelming as it grew
- Same context for every query

### After
- Retrieves top-K most **relevant** interactions using embeddings
- Semantic similarity ensures contextually related history
- Time-weighted scoring balances recency with relevance
- Context adapts to each specific query
- Knowledge base can grow indefinitely

## Architecture

### Components

1. **EmbeddingService** (`knowledge_base.py`)
   - Generates embeddings using Ollama's `nomic-embed-text` model
   - Caches embeddings to avoid redundant computation
   - Calculates cosine similarity between vectors

2. **Semantic Search** (`knowledge_base.py`)
   - `semantic_search_interactions()` method
   - Combines semantic similarity with time decay
   - Returns top-K most relevant results

3. **Enhanced Context Retrieval** (`agent_core.py`)
   - `_get_context(query)` now uses semantic search
   - Fallback to recent interactions if embeddings unavailable
   - All agent methods (chat, execute_task, respond_to_agent_message) benefit

## Setup

### Prerequisites

1. **Install Ollama** (if not already installed)
   ```bash
   # macOS
   brew install ollama
   
   # Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **Start Ollama service**
   ```bash
   ollama serve
   ```

3. **Install embedding model**
   ```bash
   ollama pull nomic-embed-text
   ```

4. **Install Python dependencies** (already in requirements.txt)
   ```bash
   pip install ollama
   ```

### Migration

If you have existing interactions in your knowledge base, run the migration script to generate embeddings:

```bash
python3 migrate_embeddings.py
```

**Options:**
```bash
python3 migrate_embeddings.py \
  --db-path data/agent.db \
  --embedding-model nomic-embed-text \
  --api-endpoint http://localhost:11434 \
  --batch-size 50
```

The script will:
- ✅ Check for Ollama availability
- ✅ Verify the embedding model is installed
- ✅ Generate embeddings for all existing interactions
- ✅ Show progress during migration
- ✅ Handle errors gracefully

## Configuration

Edit `config.yaml` to customize embedding settings:

```yaml
embeddings:
  # Embedding model (must be downloaded: ollama pull nomic-embed-text)
  model: "nomic-embed-text"
  
  # Embedding dimension (nomic-embed-text uses 768)
  dimension: 768
  
  # Number of top results to retrieve in semantic search
  top_k: 10
  
  # Time decay factor (0-1, higher = less decay)
  # 0.95 means interactions lose ~5% relevance per day
  time_decay_factor: 0.95
  
  # Size of embedding cache (number to keep in memory)
  cache_size: 1000
```

## How It Works

### 1. Embedding Generation

When an interaction is added to the knowledge base:
```python
interaction_id = kb.add_interaction(
    agent_name="my_agent",
    interaction_type="user_chat",
    content="How do I create a new agent?"
)
```

The system automatically:
1. Generates an embedding vector for the content
2. Stores it in the `embedding` column
3. Caches it for future similarity calculations

### 2. Semantic Search

When an agent needs context:
```python
# Old approach - gets last 20 interactions
context = kb.get_agent_knowledge_summary(agent_name="my_agent", limit=20)

# New approach - gets 10 most relevant interactions
context = kb.semantic_search_interactions(
    query="creating agents",
    agent_name="my_agent",
    top_k=10,
    time_decay_factor=0.95
)
```

The system:
1. Generates embedding for the query
2. Calculates cosine similarity with all stored embeddings
3. Applies time decay: `score = similarity × (decay_factor ^ days_old)`
4. Returns top-K highest scoring interactions

### 3. Time-Weighted Scoring

The scoring formula balances relevance and recency:

```
final_score = cosine_similarity × (time_decay_factor ^ days_old)
```

**Example:**
- Interaction A: 0.9 similarity, 30 days old
  - Score: 0.9 × (0.95^30) = 0.9 × 0.215 = **0.194**
  
- Interaction B: 0.7 similarity, 1 day old
  - Score: 0.7 × (0.95^1) = 0.7 × 0.95 = **0.665**

Interaction B ranks higher despite lower similarity because it's more recent.

## Testing

Run the test suite to verify functionality:

```bash
# Run full test
python3 test_semantic_search.py

# Show comparison between old and new approaches
python3 test_semantic_search.py --compare
```

The test will:
- ✅ Verify embedding generation
- ✅ Test semantic search
- ✅ Validate time-weighted scoring
- ✅ Check cosine similarity calculations
- ✅ Clean up test data

## Usage Examples

### Example 1: Agent Chat with Semantic Context

```python
from agent_core import EnhancedAgent
from knowledge_base import KnowledgeBase

# Initialize
kb = KnowledgeBase()
agent = EnhancedAgent(
    name="helper",
    model="llama3.2",
    knowledge_base=kb
)

# First conversation - about Python
agent.chat("How do I read a file in Python?")

# Second conversation - about APIs
agent.chat("How do I make an API request?")

# Third conversation - Python again
# The agent will now retrieve the first conversation
# because it's semantically relevant to Python/files
agent.chat("How do I write to a file in Python?")
```

### Example 2: Programmatic Semantic Search

```python
from knowledge_base import KnowledgeBase

kb = KnowledgeBase()

# Search for relevant interactions
results = kb.semantic_search_interactions(
    query="database configuration",
    agent_name="my_agent",
    top_k=5,
    time_decay_factor=0.95
)

for result in results:
    print(f"Relevance: {result['relevance_score']:.3f}")
    print(f"Content: {result['content']}")
    print(f"Timestamp: {result['timestamp']}")
    print()
```

### Example 3: Backfilling Embeddings

```python
from knowledge_base import KnowledgeBase

kb = KnowledgeBase()

# Generate embeddings for existing interactions
count = kb.backfill_embeddings(batch_size=50)
print(f"Generated {count} embeddings")
```

## Performance Considerations

### Memory Usage
- Embeddings are 768 floats (3KB each when stored as JSON)
- 1000 interactions ≈ 3MB of embedding data
- Embedding cache keeps frequently used embeddings in memory

### Speed
- Embedding generation: ~50-100ms per interaction (Ollama)
- Similarity calculation: ~0.1ms per comparison (pure Python)
- For 1000 interactions: ~100ms to search
- Batch processing recommended for backfilling

### Optimization Tips

1. **Adjust top_k based on use case**
   - More top_k = more context but slower/costlier LLM calls
   - Fewer top_k = faster but might miss relevant context
   - Recommended: 5-10 for most use cases

2. **Tune time_decay_factor**
   - Higher (0.98) = more weight on relevance
   - Lower (0.90) = more weight on recency
   - Recommended: 0.95 for balanced approach

3. **Use batch embedding generation**
   ```python
   # Instead of adding one at a time
   for interaction in interactions:
       kb.add_interaction(**interaction)
   
   # Use backfill after bulk inserts
   kb.backfill_embeddings(batch_size=100)
   ```

## Fallback Behavior

The system gracefully handles missing embeddings:

1. If embedding model not available → stores interaction without embedding
2. If query embedding fails → falls back to `get_agent_knowledge_summary()`
3. If interaction has no embedding → excluded from semantic search

This ensures the system continues working even if:
- Ollama is not running
- Embedding model is not installed
- Network issues prevent embedding generation

## Troubleshooting

### Problem: "model not found" error

**Solution:**
```bash
# Make sure Ollama is running
ollama serve

# Install the embedding model
ollama pull nomic-embed-text

# Verify it's installed
ollama list
```

### Problem: Embeddings not being generated

**Solution:**
```bash
# Check Ollama is accessible
curl http://localhost:11434/api/tags

# Test embedding generation
python3 -c "import ollama; print(ollama.embeddings(model='nomic-embed-text', prompt='test'))"

# Check the logs for errors
# Look for [EmbeddingService] messages
```

### Problem: Slow semantic search

**Solution:**
1. Reduce `top_k` in searches
2. Increase `batch_size` in backfill
3. Consider adding embedding cache size
4. Use interaction_type filter to narrow search space

### Problem: Results not relevant

**Solution:**
1. Check embedding model is working: `python3 test_semantic_search.py`
2. Adjust `time_decay_factor` (try 0.98 for more relevance weight)
3. Increase `top_k` to get more results
4. Verify interactions have meaningful content (not just IDs/metadata)

## Future Enhancements

Potential improvements for the semantic knowledge base:

1. **Vector Database Integration**
   - Use ChromaDB or FAISS for faster similarity search
   - Enable approximate nearest neighbor search
   - Handle millions of interactions efficiently

2. **Hybrid Search**
   - Combine semantic search with keyword matching
   - Use BM25 + embeddings for better results
   - Filter by interaction_type before semantic search

3. **Embedding Compression**
   - Use quantization to reduce storage
   - Store embeddings as binary instead of JSON
   - Use dimensionality reduction (PCA)

4. **Advanced Time Weighting**
   - Different decay rates for different interaction types
   - Boost importance of certain interactions
   - Use exponential vs linear decay

5. **Multi-Agent Context**
   - Search across multiple agents' knowledge
   - Share relevant interactions between agents
   - Build global knowledge graph

## API Reference

### EmbeddingService

```python
class EmbeddingService:
    def __init__(self, model="nomic-embed-text", api_endpoint="http://localhost:11434", cache_size=1000)
    def generate_embedding(self, text: str) -> Optional[List[float]]
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float
```

### KnowledgeBase

```python
class KnowledgeBase:
    def __init__(self, db_path="data/agent.db", embedding_model="nomic-embed-text", api_endpoint="http://localhost:11434")
    
    def semantic_search_interactions(
        self,
        query: str,
        agent_name: Optional[str] = None,
        top_k: int = 10,
        time_decay_factor: float = 0.95,
        interaction_type: Optional[str] = None
    ) -> List[Dict[str, Any]]
    
    def backfill_embeddings(self, batch_size: int = 50) -> int
```

### EnhancedAgent

```python
class EnhancedAgent:
    def _get_context(self, query: str = "") -> str
    # Note: All methods (chat, execute_task, respond_to_agent_message) 
    # now automatically use semantic search
```

## License

This semantic knowledge base implementation is part of the agent system and follows the same license.

