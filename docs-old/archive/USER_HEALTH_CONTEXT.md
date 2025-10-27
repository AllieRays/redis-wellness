# User Health Context

## Overview

The redis-wellness app supports personalized health coaching by including your medical history, injuries, and fitness goals in the LLM's system prompt. This keeps your personal health information **private** (never committed to git) while enabling context-aware health insights.

## How It Works

Your personal health context is stored in the `.env` file and injected into the system prompt when the LLM responds to queries. This allows the AI to:

- Track progress relative to injury dates
- Provide rehabilitation-focused recommendations
- Reference your specific goals and limitations
- Give personalized coaching based on your medical history

## Setup

### 1. Edit Your `.env` File

The `.env` file is **gitignored** - your personal health information stays private.

```bash
# User Health Context (Personal Medical History)
USER_HEALTH_CONTEXT="Add your personal health context here."
```

### 2. Example Context

```bash
USER_HEALTH_CONTEXT="I broke my collarbone in April 2025 and had a bone graft from my right hip for the repair. I'm currently in active recovery and rebuilding my strength gradually. When analyzing my workout data, please consider: (1) Progress relative to my April injury, (2) Upper body rehabilitation is a key focus, (3) Right hip may have some limitations from the bone graft site, (4) I'm aiming for consistent 3x/week training while respecting recovery needs."
```

### 3. What to Include

**Medical History:**
- Injuries and dates
- Surgeries or procedures
- Current recovery status
- Physical limitations

**Fitness Goals:**
- Training frequency targets
- Strength/endurance goals
- Rehabilitation objectives
- Focus areas

**Context for Analysis:**
- Progress baselines (e.g., "relative to my April injury")
- Areas to emphasize (e.g., "upper body rehabilitation")
- Limitations to respect (e.g., "right hip limitations")
- Training philosophy (e.g., "consistent 3x/week training")

## Benefits

### Context-Aware Responses

**Without Context:**
```
User: "Am I making progress?"
LLM: "Your workout count increased by 15% this month."
```

**With Context:**
```
User: "Am I making progress since my injury?"
LLM: "Yes! Since your April collarbone injury, your average workout duration has increased 71% while maintaining 3x/week consistency. Your upper body rehabilitation is progressing well."
```

### Progress Tracking

The LLM can reference your injury timeline:
- "Since your April injury..."
- "Your recovery progress shows..."
- "Relative to your surgery date..."

### Personalized Recommendations

Context enables specific guidance:
- "Given your hip bone graft site, consider..."
- "For upper body rehabilitation, focus on..."
- "To reach your 3x/week goal while respecting recovery..."

## Privacy

✅ **Your `.env` file is gitignored**
- Never committed to version control
- Stays on your local machine
- Not included in Docker images
- Not shared with anyone

✅ **Completely local**
- No external API calls
- Ollama runs on your machine
- Redis stores data locally
- 100% private health coaching

## Updating Your Context

Simply edit `.env` and restart the backend:

```bash
# 1. Edit .env file with your text editor
nano .env

# 2. Restart backend to load new context
docker-compose restart backend
```

Changes take effect immediately on next query.

## Disabling User Context

To remove personalization, clear the variable:

```bash
# In .env
USER_HEALTH_CONTEXT=""
```

The LLM will still work but won't reference your personal health context.

## Example Use Cases

### Injury Recovery Tracking
```bash
USER_HEALTH_CONTEXT="ACL surgery on left knee in March 2025. Cleared for running in June. Working on regaining full range of motion and explosive power."
```

### Chronic Condition Management
```bash
USER_HEALTH_CONTEXT="Managing Type 2 diabetes. Focus on maintaining consistent activity levels and monitoring blood sugar response to exercise. Aiming for 30 minutes daily activity."
```

### Performance Goals
```bash
USER_HEALTH_CONTEXT="Training for half marathon in October 2025. Building base mileage while preventing injury. Target: 30 miles per week by September."
```

### Post-Pregnancy Fitness
```bash
USER_HEALTH_CONTEXT="6 months postpartum. Rebuilding core strength and cardiovascular fitness. Cleared for all activities. Focus on gradual progression."
```

## Technical Details

**Implementation:**
- Stored in `.env` as `USER_HEALTH_CONTEXT` environment variable
- Loaded via Pydantic `Settings` in `backend/src/config.py`
- Injected into system prompt in `backend/src/utils/agent_helpers.py`
- Available to both stateless and stateful agents

**System Prompt Injection:**
```python
📋 USER HEALTH CONTEXT:
{your context from .env}

Consider this context when analyzing workout data, tracking progress, and providing recommendations.
Reference injury dates, recovery timelines, and goals when relevant to the user's questions.
```

## Troubleshooting

**Context not working?**
1. Check `.env` file has `USER_HEALTH_CONTEXT="your context"`
2. Ensure quotes around multi-line text
3. Restart backend: `docker-compose restart backend`
4. Verify in logs: `docker-compose logs backend | grep "USER HEALTH CONTEXT"`

**Want to verify context is loaded?**
Ask the LLM directly: "What do you know about my health history?"

## For Other Users

When sharing this codebase:

1. Copy `.env.example` to `.env`
2. Update `USER_HEALTH_CONTEXT` with their personal info
3. Their `.env` stays private (gitignored)
4. Each user gets personalized coaching

This design keeps the codebase reusable while maintaining privacy! 🎯
