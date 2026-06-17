# Chore Tracker — Template & Dashboard Recipes

These recipes show how to surface chore data in Home Assistant templates and dashboard cards using the sensors each chore exposes.

Entity IDs follow the pattern `sensor.<slug>`, where `<slug>` is a normalised version of the chore name (spaces become underscores, lower-cased). Each chore device exposes:

- `sensor.<slug>` — status (`done` / `overdue` / `snoozed`)
- `sensor.<slug>_last_completed` — timestamp of last completion (unknown until first completion)
- `sensor.<slug>_next_due` — timestamp of next overdue transition (unknown until first completion)
- `sensor.<slug>_snooze_expiry` — snooze expiry timestamp (diagnostic, disabled by default)

Substitute the entity IDs below with your own chore names.

______________________________________________________________________

## 1. Count of overdue chores

A template sensor that counts how many chores in a named subset are currently overdue. Useful on dashboards or as a condition in automations.

This approach names the sensors explicitly, which is a lighter alternative to `integration_entities('chores')` (used in `docs/automations.md`) when you only care about a specific subset of your chores.

```yaml
template:
  - sensor:
      - name: Overdue chore count
        # Returns the number of listed chores currently in the 'overdue' state
        state: >
          {{ [
               states('sensor.vacuum_living_room'),
               states('sensor.descale_kettle'),
               states('sensor.replace_smoke_alarm_batteries'),
             ] | select('eq', 'overdue') | list | count }}
        icon: mdi:clipboard-alert
```

Add this block to your `configuration.yaml` (or a file included from it). Add or remove `states('sensor.<slug>')` lines to match your own chore set.

______________________________________________________________________

## 2. Next chore due

A template sensor that returns the timestamp of the soonest upcoming chore from a named set. Pair it with a badge or a conditional card to highlight when something is coming up soon.

```yaml
template:
  - sensor:
      - name: Next chore due
        device_class: timestamp
        state: >
          {# Build a list of next-due timestamps, skipping any chore that has
             never been completed (its next_due sensor will be unavailable). #}
          {% set ns = namespace(dates=[]) %}
          {% for s in [
               'sensor.change_air_filter_next_due',
               'sensor.clean_oven_next_due',
             ] %}
            {% if has_value(s) %}
              {% set ns.dates = ns.dates + [states(s)] %}
            {% endif %}
          {% endfor %}
          {{ ns.dates | min if ns.dates else 'unknown' }}
```

`has_value(s)` returns `False` when the sensor is `unavailable` or `unknown`, which is the case for chores that have never been completed. The ISO 8601 timestamps produced by Chore Tracker sort correctly as strings, so `min` reliably returns the earliest date.

______________________________________________________________________

## 3. Markdown card

A Lovelace markdown card that lists several chores with their current status and next due date. Add it via **Dashboard → Add Card → Markdown**.

```yaml
type: markdown
content: >
  ## Chores

  | Chore | Status | Next due |
  |-------|--------|----------|
  {% for chore in [
       {'name': 'Mow lawn',       'entity': 'sensor.mow_lawn'},
       {'name': 'Water plants',   'entity': 'sensor.water_plants'},
       {'name': 'Descale kettle', 'entity': 'sensor.descale_kettle'},
     ] %}
  | {{ chore.name }}
  | {{ states(chore.entity) }}
  | {{ states(chore.entity ~ '_next_due')
        | as_timestamp
        | timestamp_custom('%d %b')
        if has_value(chore.entity ~ '_next_due') else '—' }}
  |
  {% endfor %}
```

`has_value(chore.entity ~ '_next_due')` guards against chores that have never been completed — their next-due sensor has no value yet, so `'—'` is shown instead. `timestamp_custom('%d %b')` formats the date as `24 Jun`; adjust the format string to taste.
