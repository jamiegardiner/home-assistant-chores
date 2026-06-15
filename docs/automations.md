# Chore Tracker — Automation Examples

These examples show how to wire Chore Tracker into Home Assistant automations using the three services: `chores.complete`, `chores.snooze`, and `chores.unsnooze`.

Entity IDs follow the pattern `sensor.<slug>`, where `<slug>` is a normalised version of the chore name you entered when creating it (spaces become underscores, lower-cased). Substitute the entity IDs below with your own chore names.

______________________________________________________________________

## 1. Overdue notification

Send a notification whenever a chore becomes overdue.

```yaml
alias: Notify when vacuum living room is overdue
triggers:
  - trigger: state
    # Replace with your chore entity ID: sensor.<slug>
    entity_id: sensor.vacuum_living_room
    to: overdue
actions:
  - action: notify.notify
    data:
      title: Chore overdue
      message: Time to vacuum the living room.
```

Replace `notify.notify` with your preferred notification service, such as `notify.mobile_app_your_phone`.

______________________________________________________________________

## 2. Mobile actionable notification

Send a notification with action buttons so you can mark the chore complete or snooze it directly from your phone, without opening Home Assistant. A single automation sends the notification, waits for the button tap, and handles it inline — no second automation needed.

```yaml
alias: Actionable notification when kettle descaling is overdue
triggers:
  - trigger: state
    # Replace with your chore entity ID: sensor.<slug>
    entity_id: sensor.descale_kettle
    to: overdue
actions:
  - variables:
      # Unique action names per notification instance — prevents cross-trigger collisions
      action_done: "{{ 'DESCALE_KETTLE_DONE_' ~ context.id }}"
      action_snooze: "{{ 'DESCALE_KETTLE_SNOOZE_' ~ context.id }}"
  - action: notify.mobile_app_your_phone
    data:
      title: Chore overdue
      message: Time to descale the kettle.
      data:
        actions:
          - action: "{{ action_done }}"
            title: Mark done
          - action: "{{ action_snooze }}"
            title: Snooze 1 day
  - wait_for_trigger:
      - trigger: event
        event_type: mobile_app_notification_action
        event_data:
          action: "{{ action_done }}"
      - trigger: event
        event_type: mobile_app_notification_action
        event_data:
          action: "{{ action_snooze }}"
  - choose:
      - conditions: "{{ wait.trigger.event.data.action == action_done }}"
        sequence:
          - action: chores.complete
            target:
              # Replace with your chore entity ID: sensor.<slug>
              entity_id: sensor.descale_kettle
      - conditions: "{{ wait.trigger.event.data.action == action_snooze }}"
        sequence:
          - action: chores.snooze
            target:
              # Replace with your chore entity ID: sensor.<slug>
              entity_id: sensor.descale_kettle
            data:
              value: 1
              unit: days
```

______________________________________________________________________

## 3. NFC tag → complete

Scan an NFC tag to mark a chore as done. Useful for physical locations — stick a tag near the gutters, the kettle, the bin, or wherever the chore is done.

```yaml
alias: NFC tag marks clean gutters as complete
triggers:
  - trigger: event
    event_type: tag_scanned
    event_data:
      # Replace with your NFC tag ID (found in Settings → Tags after scanning)
      tag_id: YOUR_TAG_ID_HERE
actions:
  - action: chores.complete
    target:
      # Replace with your chore entity ID: sensor.<slug>
      entity_id: sensor.clean_gutters
```

To find a tag ID: scan the tag once (the event will appear in **Settings → Automations & Scenes → Traces** or in the Developer Tools event listener), then copy the `tag_id` value into the automation above.

______________________________________________________________________

## 4. Scheduled reminder for all overdue chores

Send a daily summary notification listing every chore that is currently overdue. Useful as a morning briefing so nothing slips through.

```yaml
alias: Daily overdue chores summary
triggers:
  - trigger: time
    at: "09:00:00"
conditions:
  - condition: template
    value_template: >
      {{ states.sensor
         | selectattr('entity_id', 'in', integration_entities('chores'))
         | selectattr('state', 'eq', 'overdue')
         | list
         | count > 0 }}
actions:
  - action: notify.notify
    data:
      title: Overdue chores
      message: >
        {% set overdue = states.sensor
           | selectattr('entity_id', 'in', integration_entities('chores'))
           | selectattr('state', 'eq', 'overdue')
           | map(attribute='name')
           | list %}
        {{ overdue | join(', ') }}
```

The template uses `integration_entities('chores')` to find all entities belonging to the Chore Tracker integration, then filters for sensors in the `overdue` state. Diagnostic sensors (last completed, next due, snooze expiry) have date or datetime values so they are naturally excluded by the `overdue` state filter.
