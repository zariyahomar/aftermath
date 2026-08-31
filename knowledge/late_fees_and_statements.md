# Reading a BNPL statement

Typical fields on a confirmation email or in-app statement:
- Merchant (who you bought from)
- Provider (Klarna, Afterpay, Affirm, PayPal, Zip, etc.)
- Original order total
- Installment amount
- Remaining installments or remaining balance
- Next due date
- Late fee policy (often a flat fee per missed installment, sometimes capped)

Chunking note for retrieval: keep merchant, provider, amounts, and dates in the same chunk when possible. If a PDF splits "next payment" from the merchant name, overlap between chunks preserves that link.

Generic late-fee pattern (varies by provider and country):
- Grace periods are short or zero.
- A missed installment may still be collected; the plan does not always pause.
- Stacking several missed fees in one month is how a $15 miss becomes $60 of fees.

AfterMath should cite the user's own uploaded terms when answering fee questions. If the knowledge base and the user's document disagree, the user's document wins.
