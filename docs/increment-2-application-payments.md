# Increment 2: Application Payments

## Status and scope

Implemented as a production payment boundary for application fees: invoices, provider references,
Paystack-hosted checkout initialization, server verification, signed idempotent webhooks, finance
reconciliation, and immutable printable receipts. The domain records are gateway-neutral; Paystack
is the first adapter and its API origin is fixed in code to prevent credential-bearing requests to
an administrator-supplied URL.

This is not a general student-fees ledger. Tuition charging, instalments, refunds, chargebacks,
accounting journals, and settlement imports belong to later finance increments.

## Authoritative lifecycle

1. A Draft Admission Application with a positive configured fee gets one Application Invoice.
2. Initialization creates one active Application Payment Transaction and sends the exact amount in
   currency subunits to the provider. Retries reuse its reference and checkout URL; the secret key
   never leaves the server.
3. The applicant completes checkout on the provider-hosted page.
4. A logged-in verification request, signed webhook, or authorised manual reconciliation asks the
   provider's verification endpoint for the authoritative transaction.
5. Reference, amount, currency, and successful provider status must all match. Any mismatch is
   retained as an exception and never credits the invoice.
6. A match marks the invoice Paid and creates exactly one immutable Application Payment Receipt.
   Concurrent verification paths are serialized, so they cannot issue duplicate receipts.
7. A payment-required application may then be submitted.

## Webhook and reconciliation controls

- Endpoint: `/api/method/college_management.payments.paystack_webhook`
- The endpoint computes an HMAC-SHA512 over the raw request body using the encrypted secret and
  compares it with `x-paystack-signature` before parsing or storing the event.
- A SHA-256 payload hash is unique. Normal retries and concurrent duplicate deliveries receive an
  idempotent response and cannot repeat the financial transition. The raw provider payload is not
  retained, avoiding an unnecessary second copy of customer and payment metadata.
- Valid events are acknowledged and queued; `charge.success` is independently verified against the
  provider rather than trusted directly.
- Finance Officer, Institution Super Admin, and System Manager can invoke
  `college_management.payments.reconcile_payment` for a reference. The transaction list exposes
  Amount Mismatch, Currency Mismatch, Reference Mismatch, and Payment Not Successful exceptions.

## Deployment setup

1. In Desk, open College Management → Application Finance → Gateway Configuration.
2. Create one `Paystack` record, select Test or Live, enter the keys, and enable it. Password fields
   are encrypted by Frappe and unavailable to Applicant and Finance Officer roles.
3. In the Paystack dashboard, register the public HTTPS webhook URL shown above. Do not use
   `college.localhost` outside local development.
4. Start with test keys and perform the smoke test below before introducing live keys.
5. Restrict live credential entry to Institution Super Admin/System Manager and rotate a key if it
   is ever logged, copied to a client, or exposed outside the encrypted field.

## Smoke test

Create a Published Admission Programme with a positive Application Fee and Require Payment Before
Submission enabled. As an Applicant: create an application, call
`college_management.payments.create_application_invoice`, then
`college_management.payments.initialize_payment`; open the returned authorization URL and pay with
a provider test method. Call `college_management.payments.verify_payment` with the returned
reference. Confirm the invoice is Paid, reconciliation is Matched, one receipt exists, and the
application can submit. Repeat verification and confirm a second receipt is not created.

Automated regression command:

```bash
./bin/docker compose -p college-management-dev -f .devcontainer/docker-compose.yml exec -T \
  -w /workspace/development/frappe-bench frappe \
  bench --site college.localhost run-tests --app college_management
```
