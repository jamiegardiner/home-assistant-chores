# Chore Tracker — Troubleshooting

______________________________________________________________________

## Repair issue: corrupt `last_completed` or `snooze_until`

**Symptom:** A repair issue appears in **Settings → Repairs** reporting a corrupt `last_completed` or `snooze_until` field for a chore.

**What happened:** The stored value for one of these fields could not be parsed as a valid datetime. Chore Tracker cleared the field to `None` rather than leaving the chore in an unrecoverable state.

**Impact:** The chore continues to work normally. Clearing `last_completed` is equivalent to starting the chore fresh — it will be in the `overdue` state until you press **Complete**. Clearing `snooze_until` cancels any active snooze.

**Resolution:**

1. Go to **Settings → Repairs** and acknowledge the issue.
2. Press **Complete** on the affected chore to restore it to a known state and restart its schedule.
3. If the repair issue reappears after completing the chore, delete the entry and recreate it:
   - Go to **Settings → Devices & Services → Chore Tracker**
   - Click the three-dot menu (⋮) beside the affected chore and select **Delete**
   - Click **Add Integration**, search for **Chore Tracker**, and recreate the chore

______________________________________________________________________

## Chore fails to load entirely

**Symptom:** A chore device disappears after a restart, or an error appears in Home Assistant logs mentioning the `chores` integration failing to set up a config entry.

**What happened:** A required config field (`name` or `interval_days`) is missing or corrupt. These fields cannot be safely defaulted, so Chore Tracker refuses to load the entry rather than operating with invalid configuration.

**Resolution:**

1. Go to **Settings → Repairs** — an error-level repair issue will describe the problem.
2. Delete the affected entry:
   - Go to **Settings → Devices & Services → Chore Tracker**
   - Click the three-dot menu (⋮) beside the failed chore and select **Delete**
3. Recreate the chore:
   - Click **Add Integration**, search for **Chore Tracker**, and enter the name and interval again

______________________________________________________________________

## New chore starts in "overdue" state

**Symptom:** A newly created chore immediately shows `overdue`.

**What happened:** This is by design. A new chore has no completion history, so Chore Tracker has no basis for calculating a next-due date. Showing it as overdue prompts you to record the first completion and begin the regular cycle.

**Resolution:** Press the **Complete** button on the chore device. Chore Tracker will record the current time as the first completion and schedule the next due date from there.

______________________________________________________________________

## Verifying the integration is working

To check that a chore is tracking correctly:

1. Go to **Settings → Devices & Services → Chore Tracker**
2. Click on the chore device
3. Check the **Status** sensor — it should show `done`, `overdue`, or `snoozed`
4. Check the three diagnostic sensors in the **Sensors** section:
   - **Last completed** — when the chore was most recently marked complete
   - **Next due** — when the chore will next transition to `overdue`
   - **Snooze expiry** — when the current snooze period ends (only relevant when snoozed)

To download a full diagnostic snapshot for bug reports:

1. Open the chore device page
2. Click the three-dot menu (⋮) in the top-right corner
3. Select **Download diagnostics**

The downloaded file contains all coordinator state for the chore and can be attached to a GitHub issue.
