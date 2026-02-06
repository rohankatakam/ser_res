# Profile 01: Cold Start New User

## Summary
First-time visitor with zero engagement history. Tests quality-only ranking with no personalization signal.

**ICP Segment:** All segments  
**Duration:** 0 days (first visit)  
**Total Engagements:** 0

## Intention
This is a critical edge case — every new user starts here. The algorithm should:
- Show highest quality episodes (quality score dominates)
- Use recency as secondary factor
- Return `cold_start: true` in API response
- Label section as "Highest Signal" not "For You"

## Engagement History
*No engagements — this is a cold start profile.*
