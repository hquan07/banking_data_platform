# payment-events v1

Kafka topic: `payment-events`. Kafka key: `payment_id`. A retry must reuse the
same `event_id` and `payment_id`; a new business event gets a new `event_id`.

Required fields: `schema_version` (integer `1`), `event_id`, `trace_id`,
`payment_id`, `customer_id`, `account_id`, `amount`, `currency`,
`payment_method`, `channel`, `timestamp`, `status`.

Optional fields: `merchant_id`, `location`, `device_id`. Unknown fields may be
ignored by v1 consumers. IDs are nonempty strings. `amount` is positive, has
at most two decimal places, and is at most `99999999999.99` (the range that
the v1 JSON number representation preserves at cent precision). `currency` is a
three-letter uppercase ISO 4217 code. `timestamp` is ISO-8601 with a timezone;
producers emit UTC with `Z`. Allowed statuses: `CREATED`, `PENDING`, `SUCCESS`,
`FAILED`. Methods: `CARD`, `BANK_TRANSFER`, `QR`. Channels: `POS`, `ONLINE`,
`ATM`.

`event_id` is at most 120 characters. `trace_id`, `payment_id`, `customer_id`,
`account_id`, `merchant_id` and `device_id` are at most 50 characters;
`location` is at most 100. Amounts use plain decimal JSON numbers, without
exponential notation.

Consumers reject unknown versions and invalid required fields to
`payment-events-dlq`. Additive optional fields are compatible within v1;
breaking changes require a new schema version and a coordinated consumer
rollout. `trace_id` is retained across all stages of one request.
