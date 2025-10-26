"""
Verified Health Knowledge Base for Semantic Memory.

CRITICAL: All facts are sourced from authoritative organizations.
Every fact includes source attribution and confidence level.

Sources Used:
- Apple Health Documentation (official metrics definitions)
- American Heart Association (AHA) - cardiovascular guidelines
- Centers for Disease Control (CDC) - health recommendations
- American College of Sports Medicine (ACSM) - exercise standards
- World Health Organization (WHO) - health definitions

IMPORTANT DISCLAIMERS:
- These are GENERAL facts, not medical advice
- Individual health needs vary - encourage users to consult professionals
- Ranges are conservative and evidence-based
- Avoid specific diagnostic thresholds
"""

from typing import Any

# Fact structure:
# {
#     "fact": "The factual statement",
#     "fact_type": "definition" | "guideline" | "relationship",
#     "category": "metrics" | "cardio" | "exercise" | "nutrition" | "sleep" | "recovery",
#     "context": "Additional explanatory context",
#     "source": "Authoritative source",
#     "confidence": "high" | "medium",  # high = direct from authority, medium = derived
#     "last_verified": "2025-01" (when fact was last verified)
# }

VERIFIED_HEALTH_FACTS: list[dict[str, Any]] = [
    # ========== APPLE HEALTH METRICS (HIGH CONFIDENCE) ==========
    {
        "fact": "Active Energy represents calories burned through physical movement and exercise, excluding resting metabolism",
        "fact_type": "definition",
        "category": "metrics",
        "context": "This is different from total energy expenditure, which includes basal metabolic rate (BMR)",
        "source": "Apple Health Documentation",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Resting Heart Rate is the number of times your heart beats per minute when at complete rest",
        "fact_type": "definition",
        "category": "metrics",
        "context": "Best measured first thing in the morning before getting out of bed",
        "source": "Apple Health Documentation",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Heart Rate Variability (HRV) measures the variation in time between consecutive heartbeats",
        "fact_type": "definition",
        "category": "metrics",
        "context": "Higher HRV generally indicates better cardiovascular fitness and recovery capacity",
        "source": "Apple Health Documentation",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "VO2 Max estimates the maximum volume of oxygen your body can use during intense exercise",
        "fact_type": "definition",
        "category": "metrics",
        "context": "Measured in milliliters of oxygen per kilogram of body weight per minute (mL/kg/min). Higher values indicate better aerobic fitness",
        "source": "Apple Health Documentation, ACSM Standards",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Walking Speed measures your average pace during outdoor walks",
        "fact_type": "definition",
        "category": "metrics",
        "context": "Walking speed is a strong indicator of overall health and functional capacity, especially as we age",
        "source": "Apple Health Documentation",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Step Length is the distance covered by a single step during walking",
        "fact_type": "definition",
        "category": "metrics",
        "context": "Average step length varies by height and walking speed, typically 0.6-0.8 meters",
        "source": "Apple Health Documentation",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Double Support Time is the duration both feet are on the ground during walking",
        "fact_type": "definition",
        "category": "metrics",
        "context": "Shorter double support time generally indicates better balance and walking efficiency",
        "source": "Apple Health Documentation",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Walking Asymmetry measures the percentage of time one leg moves differently than the other during walking",
        "fact_type": "definition",
        "category": "metrics",
        "context": "Lower asymmetry (under 10%) indicates more balanced, efficient walking patterns",
        "source": "Apple Health Documentation",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    # ========== CARDIOVASCULAR HEALTH (HIGH CONFIDENCE) ==========
    {
        "fact": "A normal resting heart rate for adults ranges from 60 to 100 beats per minute",
        "fact_type": "guideline",
        "category": "cardio",
        "context": "Athletes and highly fit individuals often have resting heart rates in the 40s-50s. Factors like stress, medications, and fitness level affect resting heart rate",
        "source": "American Heart Association",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Maximum heart rate can be estimated as 220 minus your age",
        "fact_type": "guideline",
        "category": "cardio",
        "context": "This is a general formula and individual maximum heart rates can vary by ±10-20 beats per minute",
        "source": "American College of Sports Medicine",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Moderate-intensity aerobic exercise is defined as 50-70% of maximum heart rate",
        "fact_type": "guideline",
        "category": "cardio",
        "context": "At this intensity, you should be able to talk but not sing. Also called Zone 2 training",
        "source": "American Heart Association, ACSM",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Vigorous-intensity aerobic exercise is defined as 70-85% of maximum heart rate",
        "fact_type": "guideline",
        "category": "cardio",
        "context": "At this intensity, conversation is difficult. Also called Zone 3-4 training",
        "source": "American Heart Association, ACSM",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Lower resting heart rate typically indicates better cardiovascular fitness and more efficient heart function",
        "fact_type": "relationship",
        "category": "cardio",
        "context": "As cardiovascular fitness improves through aerobic training, the heart becomes more efficient, requiring fewer beats to pump blood",
        "source": "American Heart Association",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    # ========== EXERCISE GUIDELINES (HIGH CONFIDENCE) ==========
    {
        "fact": "Adults should get at least 150 minutes of moderate-intensity aerobic activity per week",
        "fact_type": "guideline",
        "category": "exercise",
        "context": "This can be broken down into 30 minutes, 5 days per week, or other combinations. Alternatively, 75 minutes of vigorous-intensity activity",
        "source": "World Health Organization, CDC",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Adults should perform muscle-strengthening activities involving major muscle groups at least 2 days per week",
        "fact_type": "guideline",
        "category": "exercise",
        "context": "This includes exercises like weight training, resistance bands, push-ups, and exercises using body weight",
        "source": "World Health Organization, CDC",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "The 'talk test' is a simple way to gauge exercise intensity during cardio activity",
        "fact_type": "guideline",
        "category": "exercise",
        "context": "Moderate intensity: you can talk but not sing. Vigorous intensity: you cannot say more than a few words without pausing for breath",
        "source": "American College of Sports Medicine",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Progressive overload is the gradual increase of stress placed on the body during training",
        "fact_type": "definition",
        "category": "exercise",
        "context": "This can be achieved by increasing weight, reps, sets, frequency, or decreasing rest time between sets",
        "source": "NSCA (National Strength and Conditioning Association)",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Cardiorespiratory fitness is inversely related to all-cause mortality risk",
        "fact_type": "relationship",
        "category": "exercise",
        "context": "Higher levels of cardiovascular fitness are associated with longer lifespan and reduced risk of chronic diseases",
        "source": "American Heart Association",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    # ========== BODY COMPOSITION & METRICS (HIGH CONFIDENCE) ==========
    {
        "fact": "Body Mass Index (BMI) is calculated as weight in kilograms divided by height in meters squared",
        "fact_type": "definition",
        "category": "metrics",
        "context": "BMI = weight(kg) / [height(m)]². BMI has limitations and doesn't account for muscle mass, bone density, or body composition",
        "source": "CDC, World Health Organization",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Basal Metabolic Rate (BMR) is the number of calories your body needs to perform basic life-sustaining functions",
        "fact_type": "definition",
        "category": "metrics",
        "context": "BMR accounts for 60-75% of daily energy expenditure and includes breathing, circulation, cell production, and nutrient processing",
        "source": "ACSM, Exercise Physiology Standards",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Total Daily Energy Expenditure (TDEE) includes BMR plus calories burned through activity and digestion",
        "fact_type": "definition",
        "category": "metrics",
        "context": "TDEE = BMR + Activity Energy + Thermic Effect of Food (TEF)",
        "source": "ACSM, Exercise Physiology Standards",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    # ========== SLEEP & RECOVERY (HIGH CONFIDENCE) ==========
    {
        "fact": "Adults aged 18-64 should aim for 7-9 hours of sleep per night",
        "fact_type": "guideline",
        "category": "sleep",
        "context": "Sleep needs vary by individual. Quality of sleep is as important as quantity",
        "source": "National Sleep Foundation, CDC",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Sleep is critical for muscle recovery, tissue repair, and cognitive function",
        "fact_type": "relationship",
        "category": "recovery",
        "context": "During deep sleep, growth hormone is released, promoting muscle growth and repair",
        "source": "National Sleep Foundation",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Active recovery involves low-intensity exercise after more intense training sessions",
        "fact_type": "definition",
        "category": "recovery",
        "context": "Examples include light walking, swimming, or yoga. Helps reduce muscle soreness and promotes blood flow",
        "source": "ACSM, Sports Medicine Guidelines",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    {
        "fact": "Adequate hydration is essential for optimal physical performance and recovery",
        "fact_type": "guideline",
        "category": "recovery",
        "context": "Even 2% dehydration can impair performance. Urine color is a simple hydration indicator (pale yellow is ideal)",
        "source": "ACSM, Sports Nutrition Guidelines",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    # ========== TRAINING CONCEPTS (MEDIUM CONFIDENCE - DERIVED) ==========
    {
        "fact": "Periodization involves systematic variation in training volume and intensity over time",
        "fact_type": "definition",
        "category": "exercise",
        "context": "Helps prevent plateaus and overtraining by organizing training into phases (base, build, peak, recovery)",
        "source": "NSCA, Periodization Theory",
        "confidence": "medium",
        "last_verified": "2025-01",
    },
    {
        "fact": "Deload weeks involve reduced training volume or intensity to allow for recovery and adaptation",
        "fact_type": "definition",
        "category": "recovery",
        "context": "Typically scheduled every 3-6 weeks, reducing volume by 40-60% while maintaining movement patterns",
        "source": "NSCA, Periodization Guidelines",
        "confidence": "medium",
        "last_verified": "2025-01",
    },
    {
        "fact": "The principle of specificity states that training adaptations are specific to the type of training performed",
        "fact_type": "relationship",
        "category": "exercise",
        "context": "Running training improves running performance, strength training builds strength. This is why cross-training has limited transfer",
        "source": "ACSM, Exercise Physiology Principles",
        "confidence": "high",
        "last_verified": "2025-01",
    },
    # ========== ADDITIONAL METRICS (HIGH CONFIDENCE) ==========
    {
        "fact": "Cadence in running refers to the number of steps taken per minute",
        "fact_type": "definition",
        "category": "metrics",
        "context": "Optimal running cadence is often cited as 170-180 steps per minute, though this varies by individual and speed",
        "source": "Running Biomechanics Research, Sports Science",
        "confidence": "medium",
        "last_verified": "2025-01",
    },
    {
        "fact": "Ground Contact Time is the duration your foot is in contact with the ground during running",
        "fact_type": "definition",
        "category": "metrics",
        "context": "Shorter ground contact times generally indicate more efficient running mechanics. Elite runners often have GCT under 200ms",
        "source": "Running Biomechanics Research",
        "confidence": "medium",
        "last_verified": "2025-01",
    },
    {
        "fact": "Vertical Oscillation measures the up-and-down movement of your torso during running",
        "fact_type": "definition",
        "category": "metrics",
        "context": "Lower vertical oscillation is generally more economical. Excessive bounce wastes energy",
        "source": "Running Biomechanics Research",
        "confidence": "medium",
        "last_verified": "2025-01",
    },
]


def get_verified_health_facts() -> list[dict[str, Any]]:
    """
    Get all verified health facts for semantic memory.

    Returns:
        List of fact dictionaries with source attribution
    """
    return VERIFIED_HEALTH_FACTS


def get_facts_by_category(category: str) -> list[dict[str, Any]]:
    """
    Get verified facts filtered by category.

    Args:
        category: Category to filter by (metrics, cardio, exercise, etc.)

    Returns:
        List of facts in that category
    """
    return [fact for fact in VERIFIED_HEALTH_FACTS if fact["category"] == category]


def get_high_confidence_facts() -> list[dict[str, Any]]:
    """
    Get only high-confidence facts (directly from authorities).

    Returns:
        List of high-confidence facts
    """
    return [fact for fact in VERIFIED_HEALTH_FACTS if fact["confidence"] == "high"]


# Medical disclaimer for UI/documentation
MEDICAL_DISCLAIMER = """
IMPORTANT MEDICAL DISCLAIMER:

This application provides general health and fitness information for educational
purposes only. The information is NOT intended to be a substitute for professional
medical advice, diagnosis, or treatment.

- Always seek the advice of your physician or qualified health provider with any
  questions about your health or a medical condition
- Never disregard professional medical advice or delay seeking it because of
  information from this application
- Individual health needs vary significantly - what works for one person may not
  work for another
- If you think you may have a medical emergency, call your doctor or emergency
  services immediately

The health knowledge in this system is sourced from authoritative organizations
(WHO, AHA, CDC, ACSM) but represents GENERAL guidelines only.
"""
