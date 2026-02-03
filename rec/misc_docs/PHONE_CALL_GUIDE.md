# Phone Call Guide — Thursday EOD Update

**For:** Personal reference during call with Rohan S.  
**Time:** ~1 hour from now  
**Goal:** Update on progress, lock assumptions, set up Monday

---

## Call Structure (Keep to 15-20 min)

### 1. Open (30 sec)
> "Hey Rohan, wanted to give you a quick EOD update on where I am with the recommendation engine and get a few quick confirmations before Monday."

### 2. What I Built (2 min)
> "Without codebase access, I reverse-engineered the web app, extracted a mock dataset, and built a working prototype with a FastAPI backend and React frontend.
>
> I have 5 recommendation sections working: Insights for You, Highest Signal, Non-Consensus Ideas, New from Your Shows, and Trending. Plus a Jump In history section to show viewed/bookmarked content.
>
> The ranking uses your insight/credibility/information scores with a credibility floor to filter out low-quality sources."

**If he asks for details:** Mention the 45/40/15 weighting and why entertainment is excluded.

### 3. Key Design Decisions (1 min)
> "A few key decisions I made:
> - Jump In is purely history, Recommendations are novel-only
> - Credibility floor of ≥2 filters out unreliable sources
> - Max 2 episodes per series to prevent one show dominating
> - Cold start shows global quality until we have 2+ views"

### 4. What I Need to Confirm (2-3 min)
**This is the most important part. Get answers.**

Say: "I have a few quick questions that would help me finalize assumptions before Monday:"

| Question | Why You're Asking |
|----------|-------------------|
| **1. Event semantics** — Is a "visit" an episode open, a play event, or a page view? Do we have listen duration/completion? | Determines how to weight signals |
| **2. Subscribed series in recs** — Should Recommendations include episodes from subscribed series, or only "New from Your Shows"? | Affects candidate generation |
| **3. Not interested** — Do we already have this signal, or should we build it? | Affects exclusion logic |
| **4. Score accessibility** — Are insight/credibility scores available in the mobile backend endpoint? | Confirms ranking is possible |

**Write down his answers.**

### 5. What I'll Send After (30 sec)
> "I'll send you a clean 1-pager after this call with the V1 spec, what I built, and the open questions documented. That way we have a reference for Monday."

### 6. Monday Setup (1 min)
> "For Monday, I'm ready for the pair programming, project walkthrough, and kickoff. Is there anything specific you want me to prep or focus on?"

### 7. Close (30 sec)
> "Thanks Rohan. I'll send the doc over shortly. Talk Monday."

---

## Quick Answers to Anticipate

**"What's the algorithm?"**
> "Hybrid approach: candidate generation from category interests, subscriptions, and global quality, then ranking with 45% insight, 40% credibility, 15% information density. Credibility floor filters out anything below 2. Diversification caps at 2 per series."

**"Why those weights?"**
> "Insight is Serafis's unique value — surfacing novel ideas. Credibility is critical for investor trust. Information density is secondary. Entertainment is excluded because this is a research tool, not a podcast app."

**"What about cold start?"**
> "New users see global Highest Signal until they've viewed 2+ episodes, then personalization kicks in."

**"What's different from Spotify?"**
> "Spotify optimizes for engagement. We optimize for intelligence quality. They don't have insight/credibility scores, and they don't have a dedicated non-consensus section."

**"What do you need from me?"**
> "Just those 4 confirmations. And if possible, read access to the codebase before Monday so I can start mapping to real tables."

---

## Red Flags to Avoid

- ❌ Don't oversell the prototype as "production-ready"
- ❌ Don't ramble about algorithm details unless asked
- ❌ Don't ask more than 4-5 questions (respect his time)
- ❌ Don't forget to offer to send the doc after

---

## Notes Section (Fill in during call)

**Event semantics answer:**


**Subscribed series in recs answer:**


**Not interested signal answer:**


**Score accessibility answer:**


**Other notes:**


---

## After the Call

1. Update the email doc with his answers
2. Send within 30 min of call ending
3. Shut down for the night
