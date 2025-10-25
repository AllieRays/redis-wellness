# 50 Questions for Stateless Agent Tool Capabilities

This document contains 50 questions that demonstrate the stateless agent's ability to use its 9 specialized Apple Health tools. These questions highlight the power of tool-calling even without memory.

## Tool Overview
The stateless agent has access to 9 tools:
1. **search_health_records_by_metric** - Query health metrics (BMI, weight, heart rate, steps)
2. **search_workouts_and_activity** - Query workout data with heart rate zones
3. **aggregate_metrics** - Calculate statistics (avg, min, max, sum, count)
4. **calculate_weight_trends_tool** - Weight trend analysis with regression
5. **compare_time_periods_tool** - Period-over-period comparisons
6. **compare_activity_periods_tool** - Comprehensive activity comparison
7. **get_workout_schedule_analysis** - Workout pattern analysis by day
8. **analyze_workout_intensity_by_day** - Workout intensity comparisons
9. **get_workout_progress** - Progress tracking between periods

---

## Health Records Search (Tool 1)

### Basic Queries
1. What was my weight in September?
2. What's my current BMI?
3. Show me my heart rate readings from last week
4. What was my step count yesterday?
5. How much water did I drink this month?

### Time-Specific Queries (Including Specific Dates)
6. What was my weight in early October 2024?
7. Show me my BMI readings from late September
8. What was my heart rate on October 15th?
9. What was my weight on Oct 22, 2024?
10. How many steps did I take in the first week of October?

---

## Workout Queries (Tool 2)

### Basic Workout Questions
11. When did I last work out?
12. Show me my recent workouts
13. What workouts did I do this week?
14. How many workouts did I complete this month?
15. What was my most recent exercise?

### Heart Rate Zone Questions
16. What was my heart rate during my last workout?
17. Which heart rate zone was I in during yesterday's run?
18. Show me my heart rate zones for this week's workouts
19. What was my average heart rate during workouts this month?
20. Did I hit maximum heart rate zone in any recent workouts?

---

## Statistics & Aggregations (Tool 3)

### Average Calculations
21. What was my average heart rate last week?
22. Calculate my average weight for September
23. What's my average daily step count this month?
24. What was my mean BMI over the last 30 days?
25. Average calories burned per workout this month?

### Min/Max Calculations
26. What was my lowest weight in October?
27. What's my highest heart rate reading this month?
28. Maximum steps in a single day last week?
29. What was my best BMI reading this year?
30. Highest calories burned in a single workout?

### Total/Sum Calculations
31. How many total steps did I take this week?
32. Total calories burned in workouts this month?
33. Sum of active energy for the last 7 days?
34. Total workout duration this week?
35. How many total workouts since September?

---

## Workout Patterns (Tools 7 & 8)

### Schedule Analysis
36. What days of the week do I typically work out?
37. How often do I exercise each week?
38. Am I consistent with my workout schedule?
39. Which day is my most common workout day?
40. What's my weekly workout frequency?

### Intensity Analysis
41. What day do I work out harder?
42. Which day has my longest workouts on average?
43. When do I push myself the most?
44. What's my hardest workout day of the week?
45. Compare workout intensity across different days

---

## Progress Tracking (Tool 9)

### Improvement Questions
46. Am I getting stronger compared to last month?
47. How has my workout frequency changed recently?
48. Have I been more active in the last 30 days?
49. Show me my progress from last month to this month
50. How do my recent workouts compare to 2 months ago?

---

## Why These Questions Work for Stateless Agent

### ✅ **Single-Turn Queries**
All questions can be answered in one interaction using tool data. The agent doesn't need to remember previous context.

### ✅ **Factual Data Retrieval**
Each question has a definitive answer in the health data. No context or memory required.

### ✅ **Tool-Powered Analysis**
Tools perform all calculations (averages, trends, patterns). The agent just formats results.

### ✅ **Self-Contained**
Each question provides all necessary information (time period, metric type, analysis needed).

### ✅ **Demonstrates Tool Value**
Without tools, these questions would be impossible to answer. With tools, answers are instant and accurate.

---

## Comparison: Where Memory WOULD Help

While the stateless agent can answer all 50 questions, here's where the **Redis RAG agent** with memory would excel:

### Follow-Up Questions (Memory Required)
- "Is that good?" (needs context of previous answer)
- "How does that compare to my goal?" (needs stored user preferences)
- "What about the week before?" (needs to remember which week was discussed)
- "And my BMI?" (needs to remember we were discussing weight)

### Contextual Preferences (Memory Required)
- "Am I on track?" (needs to know user's fitness goals)
- "Is this normal for me?" (needs historical context of user's patterns)
- "Should I be concerned?" (needs user's health context and preferences)

### Multi-Turn Conversations (Memory Required)
- User: "What was my weight last month?"
- Agent: "165 lbs"
- User: "And this month?" ← Needs memory to know we're still talking about weight
- Agent: "158 lbs"
- User: "That's good progress!" ← Conversational continuity

---

## Testing Strategy

### Test Each Tool Category
1. **Records**: Questions 1-10 (search_health_records_by_metric)
2. **Workouts**: Questions 11-20 (search_workouts_and_activity)
3. **Statistics**: Questions 21-35 (aggregate_metrics)
4. **Patterns**: Questions 36-45 (workout schedule & intensity)
5. **Progress**: Questions 46-50 (progress tracking)

### Verify Tool Usage
For each question, check that:
- ✅ Agent selected the correct tool(s)
- ✅ Tool parameters are appropriate
- ✅ Response includes accurate data from tools
- ✅ No hallucinations (numeric validator passes)
- ✅ Answer is complete in single turn

### Measure Success Metrics
- **Tool selection accuracy**: % of questions using correct tool
- **Validation score**: Average validation score across all answers
- **Response time**: Average time to answer (should be 3-15 seconds)
- **Completeness**: % of questions fully answered in one turn

---

## Usage

```bash
# Test via curl (example)
curl -X POST http://localhost:8000/api/chat/stateless \
  -H "Content-Type: application/json" \
  -d '{"message": "What was my weight in September?"}'

# Test via frontend
# Open http://localhost:3000
# Use the left panel (stateless chat)
# Try questions sequentially
```

---

## Expected Behavior

### ✅ **Good Stateless Response Pattern**
```
Question: "What was my average heart rate last week?"

Tool Called: aggregate_metrics(
  metric_types=["HeartRate"],
  time_period="last week",
  aggregations=["average"]
)

Response: "Your average heart rate last week was 72.3 bpm (based on 245 readings)."
```

### ❌ **Where Stateless Falls Short**
```
Question: "What was my average heart rate last week?"
Response: "Your average heart rate last week was 72.3 bpm."

Follow-up: "Is that good?"
Response: "I don't have context about what you're referring to. Could you clarify?"
           ↑ NO MEMORY of previous question
```

### ✅ **Where Redis RAG Agent Excels**
```
Question: "What was my average heart rate last week?"
Response: "Your average heart rate last week was 72.3 bpm (based on 245 readings)."

Follow-up: "Is that good?"
Response: "Yes, 72.3 bpm is a healthy resting heart rate. It's within the normal range
           of 60-100 bpm and indicates good cardiovascular fitness."
           ↑ REMEMBERS context of 72.3 bpm from previous answer
```

---

## Notes

- All questions are designed to be **self-contained** and answerable in **one turn**
- Questions test **all 9 tools** across different use cases
- Questions include **time periods**, **metric types**, and **analysis types** explicitly
- This set demonstrates the **value of tools** even without memory
- Compare with Redis RAG agent to see the transformative power of **memory + tools**
