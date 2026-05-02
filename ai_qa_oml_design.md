# AI Ticket QA — Service Leadership OML Redesign

**App:** AI Ticket QA (MSPbots) · `/apps/app-aiticketqa/cw`
**Author:** Product / UX working draft
**Status:** Proposal — ready for engineering refinement

---

## 1. Background

The AI Ticket QA app currently expresses ticket quality as a numeric pass rate, with each rule carrying a "Major" severity and a numeric weight. The Home page introduces a 3-tier progression model (Reactive → Proactive → Strategic).

Most MSP owners using Service Leadership's framework think in **five named OML (Operational Maturity Level) tiers** and orient their improvement work around graduating to the next level rather than maximizing a score. This document re-aligns the app to that mental model end-to-end.

### Service Leadership OML — applied definitions

- **OML 1 — Reactive ("Break/Fix mindset")**: Ad-hoc, hero-driven, inconsistent documentation, billing leakage common.
- **OML 2 — Tactical / Stabilizing ("Getting organized")**: Tickets, time entries, and agreements exist; basic hygiene enforced; categorization in use.
- **OML 3 — Efficient ("Scalable delivery")**: Standardized workflows, lifecycle/status discipline, consistent client communication, dispatch/scheduling, measurable productivity.
- **OML 4 — Effective ("Customer outcomes")**: Proactive root-cause focus, problem management, client confirmation/CSAT loops, KPI-driven, vCIO alignment.
- **OML 5 — World Class ("Continuous optimization")**: Benchmarked efficiency, predictive analytics, automation, knowledge reuse, strategic outcomes.

---

## 2. Existing Rules — Mapping to Service Leadership OML

The app currently has **14 rules across 7 domains**. Each rule is mapped below to its corresponding OML level with reasoning.

| # | Domain | Rule | OML Level | Reasoning |
|---|--------|------|-----------|-----------|
| 1 | Time Entry | Time-C3 — Ticket has ≥1 time entry | OML 2 — Tactical | Capturing labor on every ticket separates Reactive from Tactical. Without this, billing leakage and utilization reporting are impossible. |
| 2 | Ticket Hygiene | TicketHygiene-C2 — Agreement on ticket | OML 2 — Tactical | Agreement attachment is a Stabilizing-stage control that drives recurring-revenue accuracy. |
| 3 | Description Quality | Description-C2 — Clear, professional writing | OML 2 — Tactical | Basic professional writing is a hygiene precondition for any organized service desk. |
| 4 | Communication | Comm-C2 — Professional, client-safe language | OML 2 — Tactical | Hygiene/professionalism baseline; without it, the firm is still Reactive in client perception. |
| 5 | Description Quality | Description-C1 — Specific summary | OML 3 — Efficient | Specificity in the summary enables routing, dispatch, knowledge search, and pattern detection. |
| 6 | Ticket Hygiene | TicketHygiene-C1 — Accurate type/sub-type/item | OML 3 — Efficient | Categorization underpins trend analysis, technician tier routing, and reporting. |
| 7 | Technical Notes | TechNotes-C2 — What was done to fix | OML 3 — Efficient | Standardized resolution documentation enables peer review, knowledge reuse, and audit. |
| 8 | Communication | Comm-C1 — Client communication documented | OML 3 — Efficient | Documenting every client touch is part of standardized service delivery at scale. |
| 9 | Time Entry | Time-C1 — Detailed time-entry notes | OML 3 — Efficient | Quality of time-entry narrative drives accurate billing and labor analytics. |
| 10 | Time Entry | Time-C2 — Billable flag set | OML 3 — Efficient | Billable accuracy directly impacts Effective Labor Rate (ELR), an OML 3 metric. |
| 11 | Status Handling | Status-C1 — Intake → Handling → Completion | OML 3 — Efficient | Lifecycle/status discipline is the clearest indicator of a managed workflow. |
| 12 | Technical Notes | TechNotes-C1 — Suspected/confirmed root cause | OML 4 — Effective | Root-cause documentation is the precursor to problem management, an OML 4 capability. |
| 13 | Communication | Comm-C3 — Client confirmation of resolution | OML 4 — Effective | Verifying client outcome is a CSAT-discipline behavior at OML 4. |
| 14 | Time Entry | Exceeds Expected Time | OML 5 — World Class | Comparing actual labor against an expected baseline is benchmark-driven optimization. |

### Distribution today

| OML Level | Count |
|-----------|-------|
| OML 2 — Tactical | 4 |
| OML 3 — Efficient | 7 |
| OML 4 — Effective | 2 |
| OML 5 — World Class | 1 |
| **Total** | **14** |

The current ruleset is well-built for graduating from Tactical to Efficient, but light on Effective and World Class behaviors.

---

## 3. Suggested Additional Rules

Each suggested rule includes the **rule name**, **prompt text** (in the same style as existing rules so it can be pasted directly into "Add Rule"), **target OML level**, and **rationale**.

### Domain: Description Quality

*No additions — Description-C1 and Description-C2 already cover OML 2 hygiene and OML 3 specificity.*

### Domain: Ticket Hygiene

#### TicketHygiene-C3 — Priority Accuracy
- **OML Level:** OML 3 — Efficient
- **Prompt:** "The ticket priority must reasonably match the documented impact and urgency. A single-user, non-business-critical request (e.g., password reset, individual app install) should not be set to the highest priority, and a multi-user outage or business-critical failure should not be set to a low priority. Use the ticket description, affected user/asset count, and any stated business impact to judge fit; if priority cannot be determined from available evidence, do not penalize."
- **Why:** Priority drives dispatch and SLA integrity — a Service Leadership efficiency lever.

#### TicketHygiene-C4 — Single Active Owner
- **OML Level:** OML 3 — Efficient
- **Prompt:** "The ticket must have a single, currently-assigned technician (or team queue with a clear owner) at any point after Intake. Tickets that remain unassigned, are assigned to a generic 'unassigned' user, or pass between owners more than three times without documented escalation rationale should fail. Round-robin or board-level rest states are acceptable only during Intake."
- **Why:** Ownership discipline is a hallmark of dispatch maturity.

#### TicketHygiene-C5 — Configuration Item Linkage
- **OML Level:** OML 4 — Effective
- **Prompt:** "When the ticket clearly relates to a specific asset, device, or service (e.g., a server, a workstation, a SaaS tenant, a network device), the relevant Configuration Item must be linked to the ticket. Linkage is not required for purely user-administrative tasks (e.g., password resets, distribution group changes) or onboarding/offboarding templates."
- **Why:** CI linkage enables per-asset profitability and proactive lifecycle management.

### Domain: Technical Notes

#### TechNotes-C3 — Problem / Recurring Issue Linkage
- **OML Level:** OML 4 — Effective
- **Prompt:** "If the ticket addresses an issue that the technician knows or suspects has occurred before (for the same client, same user, same asset, or same application), the notes must reference the prior occurrence — either by linking to a parent ticket/problem record or by stating in the notes that the issue is recurring and what is being done about it. Single-occurrence issues are exempt."
- **Why:** Bridges incident management to problem management, a defining OML 4 capability.

#### TechNotes-C4 — Knowledge Reuse / Contribution
- **OML Level:** OML 5 — World Class
- **Prompt:** "For non-trivial resolutions (i.e., anything beyond routine setups, password resets, and standard administrative tasks), the notes must either reference an existing knowledge base article that was used, or indicate that a new/updated KB article was created based on this resolution. Trivial or templated tasks are exempt."
- **Why:** Operationalized knowledge reuse drives the optimization flywheel.

### Domain: Communication

#### Comm-C4 — First Response Within SLA
- **OML Level:** OML 3 — Efficient
- **Prompt:** "The first documented client communication (external note, email, phone, Teams, or on-site arrival) must occur within the response SLA defined by the ticket's agreement and priority. If no SLA is specified by the agreement, use the firm's default response targets by priority. Auto-generated acknowledgement emails alone do not count unless the agreement explicitly defines them as a valid first response."
- **Why:** Response-SLA discipline is a core Efficient-stage metric.

#### Comm-C5 — Client-Facing Resolution Summary
- **OML Level:** OML 4 — Effective
- **Prompt:** "At closure, the ticket must contain a client-facing summary (external note or closing email) that, in plain language, states what the issue was and what was done to resolve it. Routine service requests, setups, and administrative tasks where completion is self-evident are exempt. Internal-only resolution notes do not satisfy this rule."
- **Why:** Demonstrates outcome to the client and feeds CSAT.

### Domain: Time Entry

#### Time-C4 — Time Entry Within 24 Hours of Work
- **OML Level:** OML 3 — Efficient
- **Prompt:** "Time entries must be submitted within 24 business hours of when the work was performed. Use the difference between the time entry's work date and its created/submitted timestamp. Bulk back-entry of multiple days of time on a single date should fail unless documented blockers are noted."
- **Why:** Time-entry latency directly degrades Effective Labor Rate accuracy.

#### Time-C5 — Work-Type Accuracy
- **OML Level:** OML 3 — Efficient
- **Prompt:** "The work type / activity code on each time entry must match the actual work performed (e.g., on-site work logged as on-site, project work logged as project, after-hours work logged as after-hours). Generic catch-all work types should fail when a more specific work type clearly applies."
- **Why:** Underpins billing rate, technician utilization, and proactive-vs-reactive ratio reporting.

### Domain: Status Handling

#### Status-C2 — No Excessive Time in Holding Statuses
- **OML Level:** OML 3 — Efficient
- **Prompt:** "The ticket must not remain in a holding/waiting status (e.g., 'Waiting on Client', 'Pending', 'Scheduled') beyond the firm's defined threshold (default: 7 calendar days for Waiting on Client, 14 calendar days for Scheduled) without a documented follow-up note or status refresh. Evaluate using status-history timestamps only."
- **Why:** Prevents ticket aging — a key dispatch/scheduling discipline.

### New Domain: SLA & Outcome

#### SLA-C1 — Resolution Within SLA
- **OML Level:** OML 3 — Efficient
- **Prompt:** "The ticket's total elapsed time from creation to a Completion status must fall within the resolution SLA defined by the agreement and priority. Time spent in client-waiting statuses may be excluded if the firm's SLA policy defines it that way. If no SLA is defined by the agreement, use the firm's default resolution targets by priority."
- **Why:** Resolution-SLA is the foundational outcome metric of an efficient desk.

#### SLA-C2 — Reopen-Free Closure
- **OML Level:** OML 4 — Effective
- **Prompt:** "The ticket must not have been reopened within 7 calendar days of its first Completion status. If the ticket was reopened within that window, the notes must document the cause of the reopen and what was done differently. Customer-initiated change-of-scope reopens are exempt when documented."
- **Why:** Reopen rate is a direct quality-of-resolution measure.

### New Domain: Customer Experience

#### CSAT-C1 — CSAT/Survey Response Captured
- **OML Level:** OML 4 — Effective
- **Prompt:** "For tickets where a CSAT/NPS survey was sent, the response (or lack thereof) must be visible on the ticket. If a negative response was received, the ticket must contain a follow-up note showing the issue was acknowledged and addressed. Tickets where the agreement disables surveys are exempt."
- **Why:** Closes the customer-outcome feedback loop.

#### CSAT-C2 — Sentiment Triage
- **OML Level:** OML 5 — World Class
- **Prompt:** "If the client's notes, email, or chat content contain clearly negative sentiment (frustration, complaints, escalation language), the ticket must show a documented response addressing the sentiment — either an internal note flagging it for management review or an external response acknowledging the client's concern. Tickets with neutral/positive client communication are exempt."
- **Why:** Predictive sentiment triage is a hallmark of World Class CX operations.

### New Domain: Proactive vs. Reactive Classification

#### Proactive-C1 — Proactive/Reactive Tagging
- **OML Level:** OML 5 — World Class
- **Prompt:** "Each ticket must be classifiable (via type/sub-type, board, or a dedicated tag) as either Proactive (monitoring alert, scheduled maintenance, project work, vCIO recommendation) or Reactive (user-reported incident or request). Tickets that are ambiguous or default-categorized in a way that prevents classification should fail."
- **Why:** Tracking the Proactive Ratio is a signature Service Leadership KPI for World Class firms.

#### Proactive-C2 — Automation Candidate Flagging
- **OML Level:** OML 5 — World Class
- **Prompt:** "If the ticket matches a pattern that has occurred more than a defined threshold (e.g., 5+ times in 90 days for the same client and sub-type) and the resolution steps are repeatable, the ticket must contain a note or tag flagging it as an automation, runbook, or self-service candidate. This rule only applies once a pattern threshold is met."
- **Why:** Drives the automation/self-service flywheel central to World Class economics.

## 3.1 Complete Rules Matrix (All 29 Rules)

| # | Domain | Rule | OML Level | Type | Reasoning |
|---|--------|------|-----------|------|-----------|
| 1 | Time Entry | Time-C3 — Ticket has ≥1 time entry | OML 2 — Tactical | Existing | Capturing labor on every ticket separates Reactive from Tactical. Without this, billing leakage and utilization reporting are impossible. |
| 2 | Ticket Hygiene | TicketHygiene-C2 — Agreement on ticket | OML 2 — Tactical | Existing | Agreement attachment is a Stabilizing-stage control that drives recurring-revenue accuracy. |
| 3 | Description Quality | Description-C2 — Clear, professional writing | OML 2 — Tactical | Existing | Basic professional writing is a hygiene precondition for any organized service desk. |
| 4 | Communication | Comm-C2 — Professional, client-safe language | OML 2 — Tactical | Existing | Hygiene/professionalism baseline; without it, the firm is still Reactive in client perception. |
| 5 | Description Quality | Description-C1 — Specific summary | OML 3 — Efficient | Existing | Specificity in the summary enables routing, dispatch, knowledge search, and pattern detection. |
| 6 | Ticket Hygiene | TicketHygiene-C1 — Accurate type/sub-type/item | OML 3 — Efficient | Existing | Categorization underpins trend analysis, technician tier routing, and reporting. |
| 7 | Technical Notes | TechNotes-C2 — What was done to fix | OML 3 — Efficient | Existing | Standardized resolution documentation enables peer review, knowledge reuse, and audit. |
| 8 | Communication | Comm-C1 — Client communication documented | OML 3 — Efficient | Existing | Documenting every client touch is part of standardized service delivery at scale. |
| 9 | Time Entry | Time-C1 — Detailed time-entry notes | OML 3 — Efficient | Existing | Quality of time-entry narrative drives accurate billing and labor analytics. |
| 10 | Time Entry | Time-C2 — Billable flag set | OML 3 — Efficient | Existing | Billable accuracy directly impacts Effective Labor Rate (ELR), an OML 3 metric. |
| 11 | Status Handling | Status-C1 — Intake → Handling → Completion | OML 3 — Efficient | Existing | Lifecycle/status discipline is the clearest indicator of a managed workflow. |
| 12 | Ticket Hygiene | TicketHygiene-C3 — Priority Accuracy | OML 3 — Efficient | Suggested | Priority drives dispatch and SLA integrity — a Service Leadership efficiency lever. |
| 13 | Ticket Hygiene | TicketHygiene-C4 — Single Active Owner | OML 3 — Efficient | Suggested | Ownership discipline is a hallmark of dispatch maturity. |
| 14 | Communication | Comm-C4 — First Response Within SLA | OML 3 — Efficient | Suggested | Response-SLA discipline is a core Efficient-stage metric. |
| 15 | Time Entry | Time-C4 — Time Entry Within 24 Hours of Work | OML 3 — Efficient | Suggested | Time-entry latency directly degrades Effective Labor Rate accuracy. |
| 16 | Time Entry | Time-C5 — Work-Type Accuracy | OML 3 — Efficient | Suggested | Underpins billing rate, technician utilization, and proactive-vs-reactive ratio reporting. |
| 17 | Status Handling | Status-C2 — No Excessive Time in Holding Statuses | OML 3 — Efficient | Suggested | Prevents ticket aging — a key dispatch/scheduling discipline. |
| 18 | SLA & Outcome | SLA-C1 — Resolution Within SLA | OML 3 — Efficient | Suggested | Resolution-SLA is the foundational outcome metric of an efficient desk. |
| 19 | Technical Notes | TechNotes-C1 — Suspected/confirmed root cause | OML 4 — Effective | Existing | Root-cause documentation is the precursor to problem management, an OML 4 capability. |
| 20 | Communication | Comm-C3 — Client confirmation of resolution | OML 4 — Effective | Existing | Verifying client outcome is a CSAT-discipline behavior at OML 4. |
| 21 | Ticket Hygiene | TicketHygiene-C5 — Configuration Item Linkage | OML 4 — Effective | Suggested | CI linkage enables per-asset profitability and proactive lifecycle management. |
| 22 | Technical Notes | TechNotes-C3 — Problem / Recurring Issue Linkage | OML 4 — Effective | Suggested | Bridges incident management to problem management, a defining OML 4 capability. |
| 23 | Communication | Comm-C5 — Client-Facing Resolution Summary | OML 4 — Effective | Suggested | Demonstrates outcome to the client and feeds CSAT. |
| 24 | SLA & Outcome | SLA-C2 — Reopen-Free Closure | OML 4 — Effective | Suggested | Reopen rate is a direct quality-of-resolution measure. |
| 25 | Customer Experience | CSAT-C1 — CSAT/Survey Response Captured | OML 4 — Effective | Suggested | Closes the customer-outcome feedback loop. |
| 26 | Time Entry | Exceeds Expected Time | OML 5 — World Class | Existing | Comparing actual labor against an expected baseline is benchmark-driven optimization. |
| 27 | Technical Notes | TechNotes-C4 — Knowledge Reuse / Contribution | OML 5 — World Class | Suggested | Operationalized knowledge reuse drives the optimization flywheel. |
| 28 | Customer Experience | CSAT-C2 — Sentiment Triage | OML 5 — World Class | Suggested | Predictive sentiment triage is a hallmark of World Class CX operations. |
| 29 | Proactive vs. Reactive | Proactive-C1 — Proactive/Reactive Tagging | OML 5 — World Class | Suggested | Tracking the Proactive Ratio is a signature Service Leadership KPI for World Class firms. |
| 30 | Proactive vs. Reactive | Proactive-C2 — Automation Candidate Flagging | OML 5 — World Class | Suggested | Drives the automation/self-service flywheel central to World Class economics. |

### Recommended counts after expansion

| OML Level | Existing | Suggested | Total |
|-----------|----------|-----------|-------|
| OML 2 — Tactical | 4 | 0 | 4 |
| OML 3 — Efficient | 7 | 7 | 14 |
| OML 4 — Effective | 2 | 5 | 7 |
| OML 5 — World Class | 1 | 4 | 5 |
| **Total** | **14** | **16** | **30** |

---

## 4. UI/UX Redesign Proposal

### 4.1 What's already working on the home page
The Home page already uses the right mental model: a single headline ("You're operating Reactive"), a level track with three nodes, a streak/history strip, a "Path to Proactive" panel, a failure-distribution card, and a "Suggested Action" card. The architecture is sound — what changes is the model behind it.

### 4.2 Replace the 3-node level track with the full SLI OML 1–5 model

| Node | SLI OML Name | One-liner under headline |
|------|--------------|--------------------------|
| 1 | Reactive | "Mostly firefighting; inconsistent documentation." |
| 2 | Tactical | "Tickets, time, and agreements are captured consistently." |
| 3 | Efficient | "Standardized workflows and dispatch discipline." |
| 4 | Effective | "Outcome-driven: root cause, client confirmation, low reopens." |
| 5 | World Class | "Optimized: proactive ratio, automation, predictable margins." |

The track becomes a 5-step rail with the current level highlighted and the next level rendered as the "target."

### 4.3 Replace pass-rate % and severity weighting with rule-pass ratios per OML level
- Remove "Major" labels in Settings; remove the numeric score on the Home page.
- Each rule is tagged with the OML level it gates.
- The Home page shows, for the user's current level, how close they are to graduating — expressed as a rule-pass ratio over a rolling window.
- A user is on a level once *all* rules tagged ≤ that level are consistently passing.

### 4.4 "Path to [Next Level]" becomes the centerpiece
Rename the panel to "Focus to reach Efficient" (or whichever level is next). For each next-level rule that is not yet consistently passing, show:
- Rule name and short description
- Current pass ratio over the trailing window (e.g., "62% — needs 85%")
- Trend sparkline (last 14 days)
- "View failing tickets" link (filters QA Results to that rule)
- "View dashboard" link (rule-specific drill-down)

### 4.5 Re-frame "Share of Failures"
Today: Request/Incident/Must-Change. Re-frame to show, *within the current OML level only*, which rules contribute most to failures.

### 4.6 Re-frame "Suggested Action"
One single, specific action: the rule with the highest leverage on the next-level transition (largest gap × highest ticket volume affected).
*Example:* "Coach on TechNotes-C2 — 17 tickets failed this week. Pass rate 62%. +23 percentage points needed to graduate."

### 4.7 Settings changes (remove Major / score)
- Drop the severity selector ("major") from each rule.
- Drop the numeric weight (the "10" field).
- Add a required **OML Level** dropdown to each rule.
- Pre-populate using the mapping in Section 2.
- Inside each domain, sub-group rules by OML level.

### 4.8 New "OML Journey" page
Linked from Home → "Dive deeper." Shows the full 5-level ladder with, for each level: rules in that level, current pass-ratio, and whether the user has graduated, is currently on, or is gated by that level.

### 4.9 New "Level History" view
Replace today's 14-day dot strip with a level-history chart (configurable 30/90/180-day window) showing the OML level achieved per day.

---

## 5. Dev Ticket — Ready to Paste

### Title
AI Ticket QA — Adopt Service Leadership OML 5-Level Model; Remove Severity & Score; Redesign Home Around Level Progression

### Type / App / Priority
- **Type:** Feature / Redesign
- **App:** AI Ticket QA (`/apps/app-aiticketqa/cw`)
- **Priority:** High
- **Owner:** [Product] · [Eng Lead] · [Design]

### Background
The app currently expresses ticket quality as a numeric pass rate with per-rule "Major" severity and weight. The Home page introduces a 3-tier model (Reactive → Proactive → Strategic). Owners using Service Leadership's OML framework think in 5 named levels (Reactive, Tactical, Efficient, Effective, World Class) and orient their improvement work around graduating to the next level rather than maximizing a score. We want the app to mirror that mental model end-to-end, removing score/severity in favor of level-based progression.

### Goals
- Owners can see their current OML level and what specifically blocks them from the next level, in under 10 seconds on the Home page.
- Each QA rule is owned by exactly one OML level. There is no severity, no weight, and no numeric score anywhere in the product.
- The Home page, Settings, and a new OML Journey page consistently use SLI OML 1–5 vocabulary.

### Non-Goals
- No changes to the underlying ticket evaluation engine logic (rules pass/fail the same way).
- No changes to Write-Back, Prompt Manager, or Eval Workbench.
- No changes to PSA integrations or data ingestion.

### Scope of Changes

#### A. Data model
1. Add `oml_level` (enum: `reactive`, `tactical`, `efficient`, `effective`, `world_class`) to the Rule entity. Required, non-null.
2. Remove `severity` and `weight` from the Rule entity (or keep nullable in DB for backward compat but stop reading/writing in app).
3. Migration: pre-populate `oml_level` for all 14 existing rules using Appendix A.
4. Add a derived per-rule metric: `rolling_pass_ratio_14d` (computed from existing evaluation results).
5. Add a derived per-tenant metric: `current_oml_level` = highest level L such that every rule with `oml_level ≤ L` has `rolling_pass_ratio_14d ≥ graduation_threshold` (default 0.85, tenant-configurable).
6. Add a derived per-tenant timeseries: `oml_level_by_day` for the last 180 days.

#### B. Settings → QA Criteria
1. Remove the severity dropdown from each rule card.
2. Remove the numeric weight input.
3. Add an OML Level dropdown with the five SLI options.
4. In each domain group, render rules sub-grouped by OML level (Reactive → World Class).
5. Add tenant-level setting under General: "Graduation threshold" (default 85%) and "Evaluation window" (default 14 days).
6. Update the "Add Rule" flow to require an OML Level selection.

#### C. Home page
1. Replace the 3-node level track with a 5-node SLI OML rail.
2. Headline: "You're operating at {currentLevel}." Sub-headline shows rule-pass ratio on the current level.
3. Remove "0% pass rate," "-75 pts vs yesterday," and any numeric score.
4. Rename "Path to Proactive" panel to "Focus to reach {nextLevel}". Each row shows: rule name + description, rolling pass ratio + threshold, 14-day sparkline, link to failing tickets, link to dashboard. Empty-state when all next-level rules pass.
5. Rename "Share of Failures · Last 7 Days" to "Where {currentLevel} work is slipping" — group failures by rule, scoped to current-level rules.
6. Replace "Suggested Action" with "Today's focus" — single highest-leverage rule.
7. Replace 14-day history dot strip with a 14-day OML-level strip (color per level).

#### D. New page: OML Journey (`/apps/app-aiticketqa/cw/journey`)
1. Linked from the Home "Dive deeper" footer.
2. Render all five levels stacked vertically, each with name, one-liner, rules tagged to that level, rolling pass ratio per rule, status pill (Achieved / Current / Locked).
3. Header shows current level and a level-history chart (90/180 days, configurable).

#### E. QA Results
1. Add an "OML Level" filter chip alongside Pending/Reviewed.
2. Add an OML Level column or badge to each result row.

#### F. ROI page
- No changes in this ticket.

#### G. Rule-specific drill-down
1. Lightweight modal or page: rule name, OML level, 14-day pass-ratio chart, last-N failing tickets, link to QA Results filtered by that rule.

#### H. Copy & terminology audit
1. Replace every occurrence of "pass rate," "score," and "Major" in user-facing copy with level-progression language.
2. Update tooltips, empty states, onboarding copy.

### UX Specifications
- Visual style: keep current dark theme, typography, and rail/dot pattern.
- Level palette: Reactive `orange`, Tactical `amber`, Efficient `blue`, Effective `teal`, World Class `gold/green`.
- Empty/low-data state: when fewer than N tickets evaluated in the window, show "Not enough data to confirm level — currently inferring {level}." Default N = 20 (tenant-configurable).
- Accessibility: level rail must communicate state via icon + text, not color alone.

### Acceptance Criteria
1. No occurrence of "Major," "severity," or numeric pass-rate score is rendered anywhere in the app for end users.
2. Every rule (existing and new) has a non-null `oml_level`.
3. Home headline reflects `current_oml_level` for the tenant; refreshing the page after a successful evaluation that closes the last gap promotes the level appropriately.
4. "Focus to reach {nextLevel}" panel lists exactly the next-level rules with rolling pass ratio < graduation threshold, sorted by leverage (failed tickets desc).
5. Settings → QA Criteria does not show severity or weight controls; OML Level dropdown is required to save a rule.
6. Existing 14 rules render with their pre-populated OML levels (Appendix A) without manual editing.
7. OML Journey page renders all 5 levels with the correct rules grouped under each.
8. Level rail shows 5 nodes, current level highlighted, next level outlined as target.
9. Tenant admins can change graduation threshold and evaluation window in General settings; changes take effect immediately.
10. Copy review against SLI OML naming passes.

### Telemetry
- Track clicks on "Focus to reach {nextLevel}" rule rows, "View failing tickets," and "View dashboard."
- Track level-up and level-down events.
- Track changes to graduation threshold and evaluation window.

### Rollout
1. Feature flag: `qa_oml_v2`.
2. Stage 1: Internal tenants only. Validate level mapping and copy.
3. Stage 2: Beta tenants (5–10) for two weeks. Monitor confusion via Help & Feedback.
4. Stage 3: GA. Existing severity/weight columns kept in DB read-only for 60 days, then removed.

### Appendix A — Initial OML Level Mapping for Existing Rules

| Rule | OML Level |
|------|-----------|
| Description-C2 | Tactical |
| Description-C1 | Efficient |
| TicketHygiene-C1 | Efficient |
| TicketHygiene-C2 | Tactical |
| TechNotes-C2 | Efficient |
| TechNotes-C1 | Effective |
| Comm-C1 | Efficient |
| Comm-C2 | Tactical |
| Comm-C3 | Effective |
| Time-C1 | Efficient |
| Time-C2 | Efficient |
| Time-C3 | Tactical |
| Exceeds Expected Time | World Class |
| Status-C1 | Efficient |

### Appendix B — Glossary (for in-app tooltips)
- **OML (Operational Maturity Level):** Service Leadership's 5-level model describing how mature an MSP's service delivery is.
- **Graduation threshold:** Minimum rolling pass ratio (default 85%) a rule must hit to be considered "consistently passing."
- **Evaluation window:** Trailing window (default 14 days) over which the pass ratio is computed.
- **Current OML level:** The highest level at which every rule at that level *and below* is consistently passing.

### Open Questions
1. Do we want owners to be able to *manually pin* an OML level (e.g., for coaching) or should it always be data-driven?
2. Should "World Class" require sustained achievement (e.g., 30 days) before display, to avoid flicker?
3. Should the level-up event trigger a notification or in-app celebration?
4. For tenants with very low daily ticket volume, do we relax the threshold or extend the window automatically?

---

*End of document.*