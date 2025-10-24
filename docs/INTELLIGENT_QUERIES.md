# 50 Intelligent Health Queries - CoALA Memory Showcase

This document demonstrates the power of the CoALA (Cognitive Architecture for Language Agents) memory framework through real-world health queries. Each category shows how different memory types enable sophisticated, context-aware conversations.

## CoALA Memory Framework Overview

Our Redis-powered agent uses **4 memory types** working together:

- **Episodic Memory**: Personal events, preferences, goals, health history (RedisVL vector search)
- **Semantic Memory**: General health knowledge and learned facts (RedisVL vector search)
- **Procedural Memory**: Learned tool usage patterns and query strategies (Redis Hash)
- **Short-term Memory**: Recent conversation context (Redis List)

---

## Category 1: Short-Term Memory (Recent Context)

*These queries rely on recent conversation history to maintain context across turns.*

### Basic Follow-ups
1. "What was my average heart rate last week?"
   - **Follow-up**: "Is that good?"
   - **Follow-up**: "How does it compare to this week?"

2. "Show me my workouts from Monday"
   - **Follow-up**: "What about Wednesday?"
   - **Follow-up**: "Which day had higher intensity?"

3. "What's my step count today?"
   - **Follow-up**: "Am I on track for my goal?"
   - **Follow-up**: "What do I need to do to catch up?"

### Multi-turn Analysis
4. "Tell me about my weight trend this month"
   - **Follow-up**: "Break down the daily changes"
   - **Follow-up**: "What might explain the spike on the 15th?"

5. "Compare my activity this week vs last week"
   - **Follow-up**: "Which specific metrics improved?"
   - **Follow-up**: "Tell me more about the calorie burn difference"

---

## Category 2: Episodic Memory (Personal Context)

*These queries benefit from remembering personal preferences, goals, injuries, and health events.*

### Goal Tracking
6. "How am I progressing toward my BMI goal of 22?"
7. "Am I on track to hit 10,000 steps per day consistently?"
8. "Have I been sticking to my workout frequency goal of 4x per week?"
9. "Show me my progress on maintaining resting heart rate under 60 bpm"
10. "How's my recovery coming along since I mentioned my knee injury?"

### Personal Patterns
11. "When do I consistently push my heart rate the hardest?"
12. "What day of the week do I usually skip workouts?"
13. "Do I exercise more on weekdays or weekends?"
14. "Am I a morning or evening exerciser based on my data?"
15. "What's my longest active streak this year?"

### Injury & Recovery Context
16. "How has my workout intensity changed since I hurt my shoulder?"
17. "Am I gradually increasing activity after my recovery period?"
18. "Compare my performance now vs before my injury"
19. "Is my resting heart rate improving since I started resting more?"
20. "Show me if I'm respecting my physical therapy rest days"

---

## Category 3: Semantic Memory (Health Knowledge)

*These queries leverage learned health facts, optimal ranges, and general wellness knowledge.*

### Contextual Interpretation
21. "Is my resting heart rate of 58 bpm normal for someone my age?"
22. "My BMI is 24.3 - what does that mean for my health?"
23. "I burned 2,400 calories yesterday - is that high?"
24. "What's a healthy target heart rate zone for cardio?"
25. "How many steps per day should I aim for?"

### Trend Analysis with Context
26. "My weight dropped 3 pounds this week - is that healthy?"
27. "I'm averaging 8 hours of sleep - is that enough?"
28. "My active energy expenditure increased 20% - what does that indicate?"
29. "Heart rate variability is improving - explain what that means"
30. "My workout frequency doubled - is that sustainable?"

### Comparative Health Insights
31. "How does my activity level compare to recommended guidelines?"
32. "Am I getting enough cardiovascular exercise based on my data?"
33. "Is my weight loss pace healthy or too aggressive?"
34. "Compare my heart rate zones to optimal training zones"
35. "Are my rest days adequate for recovery?"

---

## Category 4: Procedural Memory (Tool Usage Patterns)

*These complex queries require the agent to learn efficient tool-calling sequences.*

### Multi-metric Comparisons
36. "Compare my workout intensity, calories burned, and step count between last month and this month"
   - **Tools**: `compare_activity_periods_tool`, `analyze_workout_intensity_by_day`, `aggregate_metrics`

37. "Show me all my health trends - weight, BMI, resting heart rate, and steps - over the past 3 months"
   - **Tools**: `calculate_weight_trends_tool`, `search_health_records_by_metric`, `aggregate_metrics`

38. "Which days do I work out hard, and how does my resting heart rate respond the next day?"
   - **Tools**: `analyze_workout_intensity_by_day`, `search_health_records_by_metric`, `compare_periods_tool`

### Pattern Recognition Queries
39. "Do I burn more calories on days I work out in the morning vs evening?"
   - **Tools**: `search_workouts_and_activity`, `aggregate_metrics`, `compare_activity_periods_tool`

40. "Is there a correlation between my step count and my sleep quality?"
   - **Tools**: `search_health_records_by_metric` (steps), `search_health_records_by_metric` (sleep), `compare_periods_tool`

41. "Show me my workout consistency patterns - which weeks had the best adherence?"
   - **Tools**: `get_workout_schedule_analysis`, `search_workouts_and_activity`, `aggregate_metrics`

### Progress & Goal Analysis
42. "Track my progress toward all my goals: weight, steps, workout frequency, and heart rate"
   - **Tools**: `get_workout_progress`, `search_health_records_by_metric`, `aggregate_metrics`, `calculate_weight_trends_tool`

43. "Compare my best week this year vs my worst week across all metrics"
   - **Tools**: `compare_activity_periods_tool`, `aggregate_metrics`, `search_workouts_and_activity`

44. "How has my fitness evolved over the past 6 months? Show trends in endurance, strength, and consistency"
   - **Tools**: `get_workout_progress`, `analyze_workout_intensity_by_day`, `calculate_weight_trends_tool`

---

## Category 5: Combined Memory (Full CoALA Framework)

*These showcase all 4 memory types working together for truly intelligent conversations.*

### Personalized Coaching
45. **User**: "I want to lose 5 pounds by June while maintaining my muscle mass"
   - **Agent stores**: Episodic (goal), Semantic (healthy weight loss rate)
   - **Follow-up**: "Am I on track?"
   - **Agent recalls**: Goal from episodic memory, compares current trend

46. **User**: "I feel like I'm not making progress anymore"
   - **Agent uses**: Episodic (past goals), Procedural (trend analysis tools), Short-term (recent complaints)
   - **Response**: "Actually, your step count increased 15% and resting HR dropped 3 bpm over the past month"

47. **User**: "What should I focus on this week to improve my fitness?"
   - **Agent uses**: Episodic (goals + injury history), Semantic (training principles), Procedural (multi-metric analysis)
   - **Response**: "Your cardio is strong but you haven't hit your 4x/week strength goal. Avoid high-impact given your knee recovery."

### Contextual Insights
48. **User**: "Why do I feel more tired on Thursdays?"
   - **Agent uses**: Procedural (pattern detection across workout schedule + recovery metrics), Short-term (context), Semantic (recovery knowledge)
   - **Response**: "Your hardest workouts are Tuesday/Wednesday back-to-back, leaving you under-recovered by Thursday."

49. **User**: "Am I overtraining?"
   - **Agent uses**: Episodic (injury history, recent complaints), Semantic (overtraining symptoms), Procedural (trend analysis), Short-term (context)
   - **Response**: "Your resting HR is elevated 8% and workout intensity dropped 12% this week - classic signs. Consider a rest day."

50. **User**: "Celebrate my wins with me!"
   - **Agent uses**: Episodic (goals), Procedural (progress tracking), Short-term (recent achievements), Semantic (milestone interpretation)
   - **Response**: "🎉 You hit your 10k steps goal 6 days straight, your longest streak ever! Your average heart rate improved 4 bpm, and you're 2 pounds from your target weight. Outstanding progress!"

---

## How to Test These Queries

### Setup
1. **Import health data**: `python scripts/import_health.py export.xml`
2. **Start services**: `./start.sh` or `docker-compose up`
3. **Open demo**: http://localhost:3000

### Testing Strategy

**Single Memory Type** (easier queries):
- Start with Category 1-3 queries
- Observe which memory system activates in response metadata

**Combined Memory** (advanced queries):
- Move to Category 4-5 queries
- Test multi-turn conversations
- Observe tool chaining and memory retrieval

**Memory Persistence**:
```bash
# Set a goal
"I want to reach 10,000 steps per day"

# Come back later (new session)
"How am I doing on my step goal?"  # Should recall from episodic memory
```

---

## Expected Tool Usage by Category

| Category | Typical Tool Calls | Memory Types Used | Avg Response Time |
|----------|-------------------|-------------------|-------------------|
| Short-term (1) | 1-2 | Short-term only | 3-5s |
| Episodic (2) | 2-3 | Short-term + Episodic | 5-8s |
| Semantic (3) | 2-3 | Short-term + Semantic | 5-8s |
| Procedural (4) | 3-5 | Short-term + Procedural | 8-15s |
| Combined (5) | 3-5 | All 4 memory types | 10-20s |

---

## Memory Storage Examples

### After asking query #6:
```
Episodic Memory:
  "User's BMI goal is 22"
  "User tracks BMI progress regularly"

Semantic Memory:
  "Healthy BMI range is 18.5-24.9"
  "BMI of 22 is optimal for most adults"

Procedural Memory:
  weight_goal_pattern: ["search_health_records_by_metric", "calculate_weight_trends_tool"]
```

### After asking query #47:
```
Episodic Memory:
  "User has knee injury, needs low-impact exercises"
  "User's goal: 4x strength workouts per week"
  "User's cardio fitness is strong"

Short-term Memory:
  [Previous conversation about fitness assessment]

Procedural Memory:
  fitness_assessment_pattern: ["get_workout_schedule_analysis", "analyze_workout_intensity_by_day", "compare_activity_periods_tool"]
```

---

## Demo Talking Points

### For Technical Audiences:
- "Notice how episodic memory retrieves personal goals from previous sessions"
- "Procedural memory learns optimal tool sequences, reducing iterations"
- "RedisVL semantic search finds relevant health knowledge in <50ms"

### For Business Audiences:
- "The agent remembers your goals without you repeating them"
- "It understands context: 'Is that good?' references previous answers"
- "Personalized insights based on your injury history and preferences"

### For Health/Fitness Audiences:
- "Like having a personal trainer who knows your full history"
- "Spots patterns you might miss: workout timing affects recovery"
- "Celebrates milestones and keeps you motivated toward goals"

---

## Notes on Query Complexity

**Simple queries** (1-2 tools):
- Direct data retrieval: "What's my weight today?"
- Single metric analysis: "How many workouts this week?"

**Medium queries** (2-3 tools):
- Comparisons: "Am I more active this month than last?"
- Trend analysis: "Is my weight going up or down?"

**Complex queries** (3-5 tools):
- Multi-metric patterns: "Which days do I work out hardest and how does it affect my resting HR?"
- Goal tracking with context: "Am I on track for my goals given my injury recovery?"

**The CoALA framework shines on complex queries**, where all 4 memory types work together to deliver insights a stateless agent couldn't provide.
