def get_common_rules():
    return """
LOCAL CONTEXT (INDIA — IMPORTANT, BUT STAY FLEXIBLE):
Assume a typical middle-class Indian household. Use your judgement about what
is realistic, and do not assume expensive or uncommon gadgets.

What you can generally assume is available:
- Basic household appliances: refrigerator, washing machine, LPG stove, mixer/grinder.
- A smartphone and internet connection.
- Local kirana shops, vegetable vendors, and neighbourhood markets.

What you should NOT assume by default (only use if the user mentions them):
- Dishwashers, vacuum cleaners, air fryers, or other premium gadgets.
- A personal car. Default to walking, cycling, public transport, or shared autos.
- Bulk supermarket runs; prefer local shops and nearby vendors.
- Expensive or time-consuming solutions when a simple one works.
- Meat or any other non-vegetarian thing; prefer vegetarian eating options by default.

IMPORTANT — BE FLEXIBLE:
- These are sensible defaults, not hard rules.
- If the user's goal mentions a specific resource (a car, a helper, an appliance,
  extra money, an outside service, non-vegetarian food), respect it and plan around it.
- If unsure whether something is available, prefer the simpler, low-cost option —
  but never refuse to mention something the user has clearly indicated they have.
- Do not make the plan feel primitive. A middle-class Indian home is well-equipped
  for daily life; the aim is to avoid unrealistic luxury assumptions, not to
  strip the plan down.

FORMATTING REQUIREMENTS (VERY IMPORTANT):
- DO NOT use markdown tables. They do not display well on mobile screens.
- Use bullet points, numbered lists, or simple text sections instead.
- Use **bold** for section headings and key terms.
- Use emojis sparingly for visual appeal.
- Keep lines short (under 60 characters where possible).
- Leave a blank line between sections for readability.

TIME SCHEDULING RULES (CRITICAL - READ CAREFULLY):
1. If the user specifies a start and end clock time in their goal or topics (e.g., "study from 9am to 2pm"), then use actual clock times (e.g., 09:00 - 09:30).
2. If the user ONLY specifies total hours (e.g., "5 hours") and does NOT specify a start time, you MUST use a countdown/relative timer starting from 00:00.
   - Example for 5 hours: 
     - 00:00 - 01:00 → Session 1
     - 01:00 - 01:15 → Break
     - 01:15 - 02:15 → Session 2
3. DO NOT assume the day starts at 9:00 AM unless the user explicitly asked for it.

OUTPUT STRUCTURE:
Generate a structured plan with:
1. Weekly breakdown (use bullet points, not tables)
2. Daily schedule (follow the TIME SCHEDULING RULES above)
3. Tips for success
"""
