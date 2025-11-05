Run comprehensive memory system verification:

1. **Run smoke tests**:
   ```bash
   pytest tests/test_semantic_search.py -v
   ```

2. **Check embedding model status**:
   ```bash
   python -c "from core.embedding_engine import get_embedding_engine; e = get_embedding_engine(); print(f'Model: {e.model_name}, Dim: {e.model.get_sentence_embedding_dimension()}')"
   ```

3. **Verify database migration**:
   ```bash
   sqlite3 data/MEMORY/conversations.db "PRAGMA table_info(conversations)" | grep embedding
   ```

4. **Test Turkish semantic search**:
   - Create test conversation: "Kubernetes Helm chart oluştur"
   - Search with: "Helm chart'a ekle"
   - Verify context injection (should find despite suffix difference)

5. **Check memory stats**:
   ```bash
   python scripts/memory_cli.py stats
   ```

Report any failures with specific error messages and stack traces.
