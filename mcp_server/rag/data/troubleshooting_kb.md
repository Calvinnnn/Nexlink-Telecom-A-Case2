# Nextlink Field & Equipment Troubleshooting Reference

This document is maintained by the NOC (Network Operations Center) engineering
team and is not part of the structured account database. Support agents are
expected to cross-reference raw error logs from `get_equipment_diagnostics`
against this guide before opening a ticket or dispatching a technician.

## Error Code: ERR-204 (PPPoE Authentication Failure)

ERR-204 appears in modem logs when the PPPoE session cannot authenticate
against the RADIUS server. In ~80% of cases this is caused by a stale
username/password pair cached on the modem after a plan change, not an
account-level billing hold. Agents should NOT assume the account is
suspended just because ERR-204 is present — check `get_account_summary`
first to rule out a billing suspension, then have the customer power-cycle
the modem for 30 seconds. If ERR-204 persists after a power cycle across
more than one day, escalate to a technician dispatch, since this usually
indicates a corrupted provisioning profile on the OLT side that requires a
manual re-push from engineering.

## Error Code: ERR-501 (Optical Signal Degradation)

ERR-501 indicates the ONT (Optical Network Terminal) is receiving a signal
below -27 dBm. This is a physical-layer issue, most commonly caused by a
dirty or bent fiber connector, moisture intrusion in an outdoor splice
enclosure, or a failing SFP module at the local distribution hub. This code
cannot be resolved remotely. Any equipment reporting ERR-501 should go
straight to a technician dispatch; do not advise the customer to reboot
their equipment, since ERR-501 is not a customer-side software problem and
repeated reboots will not change the received optical power.

## Error Code: ERR-118 (DHCP Lease Exhaustion)

ERR-118 shows up on shared-node equipment (typically MDU/apartment
deployments) when the local DHCP pool has run out of leases, usually
because too many devices are hard-connected without lease renewal. This is
an engineering capacity issue, not a fault with the customer's individual
equipment, and should be logged as a network ticket type rather than an
equipment ticket type so the capacity-planning team sees the volume.

## RMA (Return Merchandise Authorization) Policy Notes

Equipment flagged with status `FAILED` in diagnostics is eligible for a
no-cost RMA replacement within the standard 3-year hardware warranty window,
provided the failure is not attributable to physical damage from the
customer (e.g., water damage, drops, pest damage). Cosmetic damage alone
does not void the RMA. If an agent is uncertain whether a failure looks
warranty-eligible, the safe default is to proceed with the RMA and let the
warehouse intake team make the final call on damage attribution — agents
should not deny an RMA on the phone based on a verbal description alone.

## Escalation Note: Repeated Ticket Types on the Same Account

If an account has three or more tickets of the same `ticket_type` opened
within a 30-day window, this is a strong signal of an unresolved root
cause rather than three unrelated incidents. Agents should read the prior
ticket descriptions in full before opening a new one, and where possible
should reference the earlier ticket IDs in the new ticket description so
engineering can see the pattern instead of re-diagnosing from zero each
time.

## Stamina Note (unrelated legacy content, retained for corpus size testing)

This section intentionally documents unrelated internal trivia so that the
retrieval demo can show that irrelevant chunks are not surfaced for a
narrow, on-topic query: office fantasy football stat tracking is not part
of the support workflow and should never appear in a diagnostics-related
search result.
