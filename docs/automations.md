# Chore Tracker — Automation Examples

These examples show how to wire Chore Tracker into Home Assistant automations using the three services: `chores.complete`, `chores.snooze`, and `chores.unsnooze`.

Entity IDs follow the pattern `sensor.chore_<slug>`, where `<slug>` is a normalised version of the chore name you entered when creating it (spaces become underscores, lower-cased). Substitute the entity IDs below with your own chore names.

______________________________________________________________________

## 1. Overdue notification

Send a notification whenever a chore becomes overdue.

```yaml
alias: Notify when vacuum living room is overdue
triggers:
  - trigger: state
    # Replace with your chore entity ID: sensor.chore_<slug>
    entity_id: sensor.chore_vacuum_living_room
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

Send a notification with action buttons so you can mark the chore complete or snooze it directly from your phone, without opening Home Assistant.

This requires two automations: one to send the notification, and one to handle the button tap.

### Automation A — send the notification

```yaml
alias: Actionable notification when kettle descaling is overdue
triggers:
  - trigger: state
    # Replace with your chore entity ID: sensor.chore_<slug>
    entity_id: sensor.chore_descale_kettle
    to: overdue
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: Chore overdue
      message: Time to descale the kettle.
      data:
        actions:
          - action: DESCALE_KETTLE_DONE
            title: Mark done
          - action: DESCALE_KETTLE_SNOOZE
            title: Snooze 1 day
```

### Automation B — handle the button tap

```yaml
alias: Handle kettle descaling notification actions
triggers:
  - trigger: event
    event_type: mobile_app_notification_action
    event_data:
      action: DESCALE_KETTLE_DONE
  - trigger: event
    event_type: mobile_app_notification_action
    event_data:
      action: DESCALE_KETTLE_SNOOZE
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.action == 'DESCALE_KETTLE_DONE' }}"
        sequence:
          - action: chores.complete
            target:
              # Replace with your chore entity ID: sensor.chore_<slug>
              entity_id: sensor.chore_descale_kettle
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.action == 'DESCALE_KETTLE_SNOOZE' }}"
        sequence:
          - action: chores.snooze
            target:
              # Replace with your chore entity ID: sensor.chore_<slug>
              entity_id: sensor.chore_descale_kettle
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
      # Replace with your chore entity ID: sensor.chore_<slug>
      entity_id: sensor.chore_clean_gutters
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
         | selectattr('entity_id', 'match', 'sensor\\.chore_')
         | selectattr('state', 'eq', 'overdue')
         | list
         | count > 0 }}
actions:
  - action: notify.notify
    data:
      title: Overdue chores
      message: >
        {% set overdue = states.sensor
           | selectattr('entity_id', 'match', 'sensor\\.chore_')
           | selectattr('state', 'eq', 'overdue')
           | map(attribute='name')
           | list %}
        {{ overdue | join(', ') }}
```

The template matches every sensor whose entity ID starts with `sensor.chore_` and whose state is `overdue`. If you have other sensors with a similar naming pattern, add a more specific prefix or list the entity IDs explicitly in the condition and message template.
