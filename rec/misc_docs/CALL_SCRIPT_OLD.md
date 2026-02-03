# Phone Call Script — Step by Step

**Duration:** ~15 minutes  
**Goal:** Update on progress, confirm assumptions, set up Monday

---

## STEP 1: Open (30 seconds)

> "Hey Rohan, thanks for hopping on. I wanted to give you a quick update on where I am with the recommendation algorithm and get a few confirmations before Monday."

---

## STEP 2: High-Level Framing (30 seconds)

> "So based on the inputs you gave me — activity, bookmarks, subscriptions, category interests, plus the metadata like popularity, categories, and insight/credibility scores — I built out a V1 recommendation approach."

> "The core idea: **Recommendations show novel content only** — anything the user has already viewed or bookmarked gets filtered out."

---

## STEP 3: The 4 Sections (1-2 minutes)

> "I have **4 recommendation sections**, each using different combinations of those inputs:"

**[Say each one clearly, pause between them]**

> "**One — Insights for You.**  
> This matches the user's category interests and ranks by quality. So if someone's interested in AI and Crypto, they see the best episodes in those categories."

> "**Two — Highest Signal.**  
> This is global — top quality episodes from the past week regardless of user preferences. Good for discovery and cold start."

> "**Three — New from Your Shows.**  
> This pulls from their subscribed series, sorted by most recent. Straightforward."

> "**Four — Trending.**  
> This combines series popularity with quality in the user's top category. So if they're into AI, they see what's popular and high-quality in AI."

---

## STEP 4: Quality Score (30 seconds)

> "For quality, I'm weighting **insight at 45%** and **credibility at 40%**. The logic is: insight is what makes Serafis unique — surfacing novel ideas — and credibility matters because investors care about who's speaking."

> "I also added a **credibility floor** — anything below a 2 gets filtered out entirely, so users never see low-quality sources."

**[Pause — let him react or ask questions]**

---

## STEP 5: Exclusion & Cold Start (30 seconds)

> "All sections exclude anything the user has viewed or bookmarked. Novel content only."

> "For cold start — if someone has no category interests yet, they just see Highest Signal until we learn their preferences."

---

## STEP 6: Transition to Questions (15 seconds)

> "That's the approach. I have a few quick questions to lock down assumptions before Monday — should only take a minute."

---

## STEP 7: Ask Confirmations (1-2 minutes)

**[Ask one at a time, write down his answers]**

> **Question 1:**  
> "For user activity — is a 'visit' an episode open, a play start, or just a page view? I want to make sure I'm treating that signal correctly."

**[Wait for answer, write it down]**

> **Question 2:**  
> "You mentioned insight and credibility scores — is there also an information score, or just those two?"

**[Wait for answer, write it down]**

> **Question 3:**  
> "For subscribed series — should those episodes **only** appear in 'New from Your Shows', or can they also appear in other sections like Insights for You?"

**[Wait for answer, write it down]**

---

## STEP 8: Offer to Send Doc (15 seconds)

> "Great, that helps. I'll send you a one-pager after this with the full breakdown — inputs, sections, formulas — so we have a reference for Monday."

---

## STEP 9: Monday Setup (30 seconds)

> "For Monday — I'm ready for the pair programming, project walkthrough, and kickoff. Is there anything specific you want me to prep or focus on before then?"

**[Wait for his response]**

---

## STEP 10: Close (15 seconds)

> "Perfect. Thanks Rohan — I'll send the doc over shortly. Looking forward to Monday."

---

## NOTES SECTION (Fill in during call)

**Q1 — What is a "visit"?**  
Answer: _________________________________

**Q2 — Information score exists?**  
Answer: _________________________________

**Q3 — Subscribed series in other sections?**  
Answer: _________________________________

**Anything else he mentioned:**  
_________________________________
_________________________________

---

## IF HE ASKS...

**"What about entertainment score?"**
> "I excluded it from the quality formula — this is a research tool, not a podcast app, so entertainment doesn't map to user value here."

**"What about Non-Consensus / contrarian content?"**
> "I prototyped it using critical_views data, but I want to confirm that field is reliable before committing to V1. Could be a V1.5 addition."

**"What about Jump In?"**
> "That's the history interface — I understood it's separate from recommendations. I have it working but didn't focus on it since you said the rec algo is the priority."

**"What about descriptions / embeddings?"**
> "That's V2. For V1 I'm using the structured signals you provided. Embeddings would let us do content similarity, but that's a second iteration."

**"Can you show me the prototype?"**
> "Happy to — I can share my screen or send you the repo. It's a React frontend with a FastAPI backend using mock data I extracted from Serafis."

---

## AFTER THE CALL

1. Update `EMAIL_FOCUSED.md` with his answers
2. Send within 30 minutes
3. **Done for the night**
