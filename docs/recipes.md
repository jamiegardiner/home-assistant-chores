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

## 2. Next chore due in a room

A template sensor that returns the name of the chore with the soonest next-due date within a given HA area. Requires chore devices to be assigned to an area in **Settings → Areas & Zones**, and requires the `next_due` attribute on the status sensor (see [#196](https://github.com/jamiegardiner/home-assistant-chores/issues/196)).

Replace `kitchen` with your area name (lower-cased, spaces as underscores).

```yaml
template:
  - sensor:
      - name: Next chore due in kitchen
        state: >
          {% set ns = namespace(name=none, ts=none) %}
          {% for eid in integration_entities('chores') | select('in', area_entities('kitchen')) %}
            {% set t = state_attr(eid, 'next_due') | as_timestamp(none) %}
            {% if t is not none and (ns.ts is none or t < ns.ts) %}
              {% set ns.ts = t %}
              {% set ns.name = state_attr(eid, 'friendly_name') %}
            {% endif %}
          {% endfor %}
          {{ ns.name if ns.ts is not none else 'unknown' }}
        icon: mdi:clipboard-clock
```

`integration_entities('chores')` scopes the search to Chore Tracker entities only, and `select('in', area_entities('kitchen'))` narrows it to the room. `next_due` is `none` for chores that have never been completed, so they are automatically skipped. The sensor state is `unknown` when no chores in the area have a next-due date yet.

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
