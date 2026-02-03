# Phone Call Guide — FOCUSED Version

**Goal:** Stay on the recommendation algorithm. Don't go off-track.

---

## What to SAY (Keep it tight)

### Open (30 sec)
> "Hey Rohan, quick update on the recommendation algorithm. I focused on exactly the inputs you provided — activity, bookmarks, subscriptions, category interests, plus the metadata."

### The Algorithm (2 min)
> "I have 4 recommendation sections:
> 
> 1. **Insights for You** — matches category interests, ranked by quality
> 2. **Highest Signal** — global top quality for all users
> 3. **New from Your Shows** — latest from subscribed series
> 4. **Trending** — popular + quality in user's top category
>
> Quality score is 45% insight, 40% credibility, 15% information. I also added a credibility floor — anything below 2 gets filtered out entirely."

### Exclusion Logic (30 sec)
> "All recommendations exclude anything the user has viewed or bookmarked. Novel content only."

### Cold Start (30 sec)
> "New users with no category interests see Highest Signal until we learn their preferences."

### Confirmations (1-2 min)
> "A few quick questions to finalize:"

1. **"Is 'visit' in activity a play event, or just opening the episode?"**
2. **"You mentioned insight and credibility scores — is there also an information score, or just those two?"**
3. **"Should subscribed series episodes ONLY appear in 'New from Your Shows', or also in other sections?"**

### Close (30 sec)
> "I'll send you a 1-pager after this. Ready to wire it to real data Monday."

---

## What NOT to say

- ❌ Don't mention Jump In (he said it's not the focus)
- ❌ Don't mention Org Discovery Bridge (that's search, not recs)
- ❌ Don't mention competitor research (Spotify/Apple)
- ❌ Don't mention Non-Consensus section unless he asks (it depends on critical_views which may not be confirmed)
- ❌ Don't oversell the prototype — it's validation, not production

---

## If He Asks...

**"What about Non-Consensus Ideas?"**
> "I prototyped it using the critical_views field, but I want to confirm that data is reliable before committing it to V1. Could be V1.5."

**"What about Jump In?"**
> "I understood that's the history interface, separate from recommendations. I have it working in the prototype but didn't focus on it since you said the rec algo is the priority."

**"What about [something else]?"**
> "Good question — let me note that and we can discuss Monday. For V1 I focused on the core sections you specified."

---

## Notes Section (Fill in during call)

**Visit event = ?**


**Scores available in API?**


**Subscribed series in other sections?**


**Other:**


---

## After Call

1. Send `EMAIL_FOCUSED.md` (update with his answers first)
2. Done for the night
