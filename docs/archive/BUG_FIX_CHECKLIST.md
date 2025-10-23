# Bug Fix Checklist

Quick reference for implementing the bug fixes.

## 🎯 Phase 1: Memory Confusion Fix

### Investigation
- [ ] Examine `backend/src/services/memory_manager.py`
- [ ] Check how semantic search is currently called
- [ ] Verify Redis key structure: `conversation:{session_id}`
- [ ] Test current behavior with "What was the first thing I asked?"

### Implementation
- [ ] Add `scope` parameter to `search_memories()` function
- [ ] Implement `_get_session_history()` method
- [ ] Implement `_search_semantic_excluding_session()` method
- [ ] Create `classify_memory_need()` function in agent
- [ ] Update agent system prompt with memory usage guidelines
- [ ] Modify chat route to classify memory scope before retrieval
- [ ] Update agent to format context based on scope

### Testing
- [ ] Test: "What was the first thing I asked?" → should return THIS session
- [ ] Test: "What are my fitness goals?" → should use semantic memory
- [ ] Test: Mixed queries work appropriately
- [ ] Verify no regression in existing functionality

### Files Modified
- [ ] `backend/src/services/memory_manager.py`
- [ ] `backend/src/agents/health_rag_agent.py`
- [ ] `backend/src/api/chat_routes.py`

---

## 🎯 Phase 2: Pronoun Resolution

### Implementation
- [ ] Create new file: `backend/src/utils/context_tracker.py`
- [ ] Implement `ConversationContext` class
- [ ] Add `update_from_query()` method
- [ ] Add `update_from_response()` method
- [ ] Add `resolve_pronoun()` method
- [ ] Add serialization methods (`to_json()`, `from_json()`)
- [ ] Integrate into chat route (load, update, save)
- [ ] Store context in Redis with 7-day TTL
- [ ] Update agent prompt with pronoun handling guidelines

### Testing
- [ ] Test: Q1="What's my BMI?", Q2="Is that healthy?" → understands "that"=BMI
- [ ] Test: Various pronoun types: "that", "it", "this"
- [ ] Test: Context tracking across multiple turns
- [ ] Test: Context expiration after 7 days

### Files Created/Modified
- [ ] NEW: `backend/src/utils/context_tracker.py`
- [ ] MODIFIED: `backend/src/api/chat_routes.py`
- [ ] MODIFIED: `backend/src/agents/health_rag_agent.py`

---

## 🎯 Phase 3: Test Data Generation

### Implementation
- [ ] Create new file: `backend/tests/fixtures/generate_health_data.py`
- [ ] Implement BMI data generation (90 days, daily)
- [ ] Implement weight data generation (3x per week)
- [ ] Implement heart rate data generation (5-10x per day)
- [ ] Calculate summaries and metadata
- [ ] Create loading script: `scripts/load_test_data.sh`
- [ ] Make script executable
- [ ] Run script to populate Redis

### Verification
- [ ] Query BMI data → should return actual values
- [ ] Query weight data → should return actual values
- [ ] Query heart rate data → should return actual values
- [ ] Check data spans September (for test queries)
- [ ] Verify ~2000+ total records generated

### Files Created
- [ ] NEW: `backend/tests/fixtures/generate_health_data.py`
- [ ] NEW: `scripts/load_test_data.sh`

---

## 🎯 Phase 4: Verification

### Targeted Bug Tests
- [ ] Create `tests/test_bug_fixes.sh`
- [ ] Test Bug #1: Session memory isolation
- [ ] Test Bug #2: Pronoun resolution
- [ ] Test Bug #3: Data availability
- [ ] Make script executable
- [ ] Run and verify all tests pass

### Re-run Full Test Suite
- [ ] Run `./test_chat_comparison.sh`
- [ ] Save results to `results_after_fixes.txt`
- [ ] Compare with original `TEST_RESULTS.md`
- [ ] Document improvements
- [ ] Update `HONEST_TEST_RESULTS.md` with new findings

### Documentation
- [ ] Update README with bug fix notes
- [ ] Document new memory scope feature
- [ ] Document pronoun resolution feature
- [ ] Add examples of improved behavior
- [ ] Update API documentation if needed

---

## 📊 Success Metrics

### Before Fixes:
- ❌ Session memory recall: 0% (Bug #1)
- ❌ Pronoun resolution: 0% (Bug #2)
- ❌ "No data" responses: 70% (Bug #3)
- ⚖️ Redis RAG wins: 1/10 tests

### Target After Fixes:
- ✅ Session memory recall: >95%
- ✅ Pronoun resolution: >80%
- ✅ "No data" responses: <10%
- ✅ Redis RAG wins: >5/10 tests (clear superiority)

---

## 🚨 Red Flags to Watch For

### During Implementation:
- [ ] Breaking changes to existing API contracts
- [ ] Increased latency (>100ms)
- [ ] Memory leaks in context tracking
- [ ] Redis storage bloat

### During Testing:
- [ ] Any test that was passing now fails
- [ ] Semantic memory stops working
- [ ] Tool calling breaks
- [ ] Session isolation breaks

### In Production:
- [ ] Increased error rates
- [ ] User complaints about wrong context
- [ ] Redis out of memory
- [ ] Slower response times

---

## 🔄 Rollback Triggers

Roll back immediately if:
1. **Critical bug found** that breaks existing functionality
2. **Performance degradation** >200ms per request
3. **Error rate increase** >5% over baseline
4. **User satisfaction drop** in first 24 hours

Rollback procedure:
```bash
git revert <commit-hash>
docker-compose up --build -d
# Test rollback successful
./test_chat_comparison.sh
```

---

## 📝 Commit Strategy

### Phase 1 Commits:
1. `feat: add memory scope parameter to search_memories()`
2. `feat: add memory classification for session vs semantic`
3. `feat: integrate memory scope into chat route`
4. `test: add tests for memory scope classification`

### Phase 2 Commits:
1. `feat: add ConversationContext tracker for pronouns`
2. `feat: integrate pronoun resolution into chat route`
3. `feat: add pronoun handling to agent prompt`
4. `test: add tests for pronoun resolution`

### Phase 3 Commits:
1. `test: add health data generator for comprehensive testing`
2. `test: add script to load test data into Redis`
3. `docs: update testing documentation`

### Phase 4 Commits:
1. `test: add targeted bug fix verification tests`
2. `docs: update results with post-fix analysis`
3. `docs: document bug fixes and improvements`

---

## 🎉 Definition of Done

All phases complete when:
- [ ] All checklist items above are checked
- [ ] All tests pass (existing + new)
- [ ] Code reviewed by team
- [ ] Documentation updated
- [ ] Performance benchmarks meet targets
- [ ] Staged deployment successful
- [ ] Production rollout complete
- [ ] Post-deployment monitoring shows improvement
- [ ] User feedback positive

---

## 📞 Need Help?

### Common Issues:

**"Memory scope not working"**
- Check Redis keys are session-scoped
- Verify `classify_memory_need()` returns correct scope
- Check agent prompt includes memory guidelines

**"Pronoun resolution fails"**
- Verify `ConversationContext` is saved to Redis
- Check TTL hasn't expired
- Verify `resolve_pronoun()` logic matches patterns

**"Test data not showing up"**
- Check Redis connection
- Verify key structure matches expected format
- Check data generator produces correct date ranges

---

## 🚀 Quick Start

```bash
# 1. Create feature branch
git checkout -b fix/memory-and-context-bugs

# 2. Implement Phase 1
# ... make changes ...
git commit -am "Phase 1: Memory scope classification"

# 3. Test Phase 1
./tests/test_memory_scope.sh

# 4. Implement Phase 2
# ... make changes ...
git commit -am "Phase 2: Pronoun resolution"

# 5. Generate test data (Phase 3)
./scripts/load_test_data.sh

# 6. Run full verification
./tests/test_bug_fixes.sh

# 7. Re-run comparison
./test_chat_comparison.sh > results_after_fixes.txt

# 8. Review and merge
git push origin fix/memory-and-context-bugs
# Create PR, get review, merge
```
