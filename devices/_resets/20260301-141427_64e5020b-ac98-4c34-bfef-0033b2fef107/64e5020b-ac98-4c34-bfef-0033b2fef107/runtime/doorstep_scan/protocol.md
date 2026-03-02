# Doorstep Conditions Scan Protocol

Purpose: Reduce avoidable departure disruptions with a short local check and three concrete actions.

Cadence (local time):
- Morning scan window: 06:30-09:00
- Evening scan window: 17:00-20:00

2-minute doorstep checklist:
- Precipitation: none | light | moderate | heavy
- Wind: calm | breezy | strong
- Visibility: clear | reduced | poor
- Walking surface: dry | damp | wet | slippery | obstructed

Action-tip rules (publish exactly 3 tips):
- If precipitation is light/moderate/heavy: carry an umbrella and wear a water-resistant outer layer.
- If wind is strong: secure outerwear and avoid exposed route segments.
- If visibility is reduced/poor: add a high-visibility layer and allow a 10-minute travel buffer.
- If surface is wet/slippery: wear slip-resistant footwear and choose the safer route.
- If surface is obstructed: use an alternate exit path and avoid carrying bulky items.
- If all conditions are clear: normal departure, plus a lightweight backup layer.

Log record fields:
- ts
- slot (morning|evening|setup)
- precipitation
- wind
- visibility
- surface
- action_tips (3 items)
- confidence (observed|inferred|unknown)
- notes
