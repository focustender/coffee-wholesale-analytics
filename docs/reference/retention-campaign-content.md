# Retention campaign content

Five lifecycle-stage relationship programs, plus one flagship segment, built
for Coffee Wholesale Analytics' 500 real-linked HubSpot contacts. Segment
membership is confirmed live via `analysis/segment_retention_campaigns.py`
after `integrations/sync_lifecycle_stage.py` has run; the numbers below are
from that data (real business_type LTV from `data/customers.csv`, real
segment counts from HubSpot's `wholesale_lifecycle_stage` property).

**Deliberately not a generic drip sequence.** Each stage gets one message
because each stage represents a different relationship problem, not a step
in a single funnel. Lead is excluded on purpose -- that's an acquisition
question, not a retention one, and stretching this project to cover it would
dilute the actual finding below.

**Not sent.** These are drafted, reviewable copy, the same standard Trade
Signal held its own designs to before calling anything "live." A free/dev
HubSpot portal doesn't have Marketing Hub email-send access either way, so
the honest scope here is: real segments, real numbers, real copy, no send.

## The value tier

`avg lifetime_value` by `business_type` (`analysis/follow_on_analysis.py`,
confirmed live in `segment_retention_campaigns.py`): cafe $8,185, hotel
$4,769, restaurant $3,517, gym $1,113. Cafe stands alone as **High**; hotel
and restaurant cluster close enough to group as **Mid**; gym is **Low**. This
tier doesn't create five separate campaigns per stage -- it modulates
*channel and effort* within each one, noted per stage below.

## New Account

**Relationship goal:** the account has placed one order and nothing about
the relationship is proven yet. The job here isn't a second sale, it's
establishing a real point of contact before the account defaults to treating
this as a transactional vendor relationship. Every account skipped here is
one more account with no human relationship to fall back on if something
goes wrong later.

**Tone:** personal, curious, low-pressure. No upsell.
**Channel / cadence:** one email, 2-3 weeks after the first order, from a
named account contact, not a marketing address.
**Tier note:** High tier gets a phone call instead of an email; the
relationship is worth establishing by voice from day one.

> **Subject:** How's the [origin] working out for you?
>
> Hi [first name] -- wanted to check in now that you've had a few weeks with
> the [origin] from your first order. How's it going behind the bar? If
> anything about brew ratio, roast rotation, or how billing/reorders work
> would be useful to walk through, just reply -- I'm your point of contact
> for [Company], not a ticket queue.

## Active Account

**Relationship goal:** this is the largest group with the most to lose
quietly. Nothing is wrong yet, which is exactly the risk -- an account that's
ordering normally gets no attention until it stalls, at which point it's
already At-Risk. The goal is a relationship touch before there's a problem
to react to.

**Tone:** appreciative, genuinely curious about their business, not a check-in
disguised as a sales call.
**Channel / cadence:** quarterly, paired with something useful (e.g. the
next origin rotation) rather than a bare "checking in."
**Tier note:** Mid/Low tier stays email; High tier gets the same email plus
a standing open invite to a roaster call.

> **Subject:** What's coming up for [Company] this quarter
>
> Hi [first name] -- the [next origin] rotation starts next month, thought
> you'd want a heads-up before it's live. Separately: anything about your
> current orders that's not working as well as it could -- pace, pack size,
> delivery timing? Would rather hear it now than guess later.

## Established Account

**Relationship goal:** these are the accounts a business assumes are safe,
which is precisely how complacency-driven churn happens -- the relationship
gets no attention *because* it looks fine. The goal is recognition, not
retention messaging that would read as needy for an account this settled.

**Tone:** recognition, insider access, no sales framing at all.
**Channel / cadence:** roughly annual, tied to their tenure or order
milestone.
**Tier note:** High tier gets first access to limited-run origins before
they're announced broadly; Mid/Low get the recognition note without the
early-access hook.

> **Subject:** [Company] has been with us for [X] -- something for you first
>
> [First name] -- you've been ordering [primary origin] with us since [year],
> which puts [Company] among our longest-standing accounts. Before we
> announce it more broadly: [new origin] is available to a short list of
> accounts first, and you're on it. No obligation, just wanted you to see it
> before the general list does.

## At-Risk

**Relationship goal:** something changed and nobody asked why. The instinct
is to lead with a discount; the better move is to lead with a genuine
question, because a discount answers a price objection that may not be the
actual reason -- a bad last shipment, a menu change, a competitor's rep
showing up at the right moment, or nothing at all. Guessing the reason and
offering the wrong fix burns the relationship a second time.

**Tone:** direct concern, not guilt, no assumption about why.
**Channel / cadence:** personal outreach within a week of the stage flip.
**Tier note:** this is where the tier split matters most, and it's the
project's real finding: 26 accounts are At-Risk with $104,850 combined
lifetime value at stake, and cafes are only 38.5% of that count but **55.4%
of that revenue** ($58,058 of $104,850). A campaign that emails all 26
equally is spending the same effort on segments worth very different
amounts.

- **High tier (cafe, $58,058 at stake across 10 accounts):** a phone call
  from the account manager, not an email. Worth the higher-touch channel at
  this concentration of revenue.
- **Mid/Low tier ($46,792 across 16 accounts):** a personal but email-based
  version of the same question.

> **Subject (Mid/Low, email):** Has something changed on your end?
>
> [First name] -- noticed it's been a while since your last order from
> [Company], and wanted to check in directly rather than assume. Did
> something happen with the last shipment, or has your ordering just shifted
> around? Either way, happy to help however's useful -- no pitch attached to
> this note.

> **Call talking points (High tier, phone):** Open with the same genuine
> question, not a discount offer. Listen for the actual reason before
> proposing anything. If price comes up specifically, that's the moment to
> discuss terms -- not before.

## Churned

**Relationship goal:** the account made a choice. Respecting it is itself a
relationship move -- continuing to chase a churned account past one graceful
note reads as pressure, not care, and damages the chance they'd come back on
their own terms later.

**Tone:** gracious, brief, no guilt, no second follow-up if unanswered.
**Channel / cadence:** one email, then stop.

> **Subject:** The door's open if things change
>
> [First name] -- noticed [Company] hasn't ordered in a while, and wanted to
> send one note rather than a series: if anything ever changes, we'd welcome
> you back, no questions asked. No need to reply to this one either way.

## What this deliberately doesn't do

No fabricated open/click rates, no simulated campaign results -- the same
rule Trade Signal held itself to for its experiment (a fabricated outcome
would look more impressive and be dishonest). These are drafted for review,
grounded in real segment numbers pulled live from HubSpot; whether they
convert is a question for an actual send, which is out of scope for a
free/dev portal.
