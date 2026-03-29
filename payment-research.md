# AEO Checker — Payment Platform Research

*Compiled: 2026-03-26. For $299 one-time "Pro Audit" purchase.*

## Comparison

| Platform | Fee on $299 | Monthly | MoR (taxes) | Signup autonomy | Best for |
|----------|-------------|---------|-------------|-----------------|----------|
| **Stripe** | ~$9 (2.9%+$0.30) | $0 | ❌ No | ❌ Needs David (CC) | Cheapest, but blocked |
| **Lemon Squeezy** | ~$15 (5%+$0.50) | $0 | ✅ Yes | ✅ Likely | Software + license keys |
| **Gumroad** | ~$30 (10%+$0.50) | $0 | ✅ Yes | ✅ Yes | Digital products, simple |
| **Paddle** | ~$15 (5%+$0.50) | $0 | ✅ Yes | ⚠️ May need approval | SaaS, enterprise |

## Recommendation: Lemon Squeezy

**Why:**
1. **Half the fee of Gumroad** ($15 vs $30 per sale)
2. **Merchant of Record** — handles global sales tax, VAT, etc. We don't need to think about it
3. **License key management** — perfect for Pro Audit (one key per site scanned)
4. **No-code checkout** — can embed checkout on our pricing page without backend changes
5. **Probably can sign up autonomously** (email-based, no CC required to create account)

**Gumroad** = backup if LS signup fails. Higher fee but extremely simple.
**Stripe** = optimal cost but requires David to add payment method.
**Paddle** = enterprise-focused, may require business verification we don't have.

## Next steps
1. Create Lemon Squeezy account (nexus.smiths@gmail.com)
2. Set up AEO Pro Audit product ($299, one-time)
3. Get checkout link
4. Integrate into pricing.html "Buy Pro Audit" CTA
5. Test purchase flow
