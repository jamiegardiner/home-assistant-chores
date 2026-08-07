# Changelog

## [1.3.0](https://github.com/jamiegardiner/home-assistant-chores/compare/v1.2.0...v1.3.0) (2026-08-07)


### Features

* **issue-211:** persist next_due in config entry options ([#221](https://github.com/jamiegardiner/home-assistant-chores/issues/221)) ([a56404a](https://github.com/jamiegardiner/home-assistant-chores/commit/a56404adbb745dbb4a6a6acc8a7af6e2d8aa22a8))
* **issue-218:** add notification_time to primary sensor's extra_state_attributes ([#219](https://github.com/jamiegardiner/home-assistant-chores/issues/219)) ([230c06a](https://github.com/jamiegardiner/home-assistant-chores/commit/230c06a9c26f65c2d29f347686ce5c420599e6e5))

## [1.2.0](https://github.com/jamiegardiner/home-assistant-chores/compare/v1.1.0...v1.2.0) (2026-06-19)


### Features

* **issue-184:** promote next_due and last_completed to primary sensors; disable snooze_until by default ([#185](https://github.com/jamiegardiner/home-assistant-chores/issues/185)) ([2f8cf85](https://github.com/jamiegardiner/home-assistant-chores/commit/2f8cf85b0b8c67e15c492ef861224d2a5f492f8a))
* **issue-186:** rename "Notification Time" label to "Overdue time" ([#188](https://github.com/jamiegardiner/home-assistant-chores/issues/188)) ([df4c880](https://github.com/jamiegardiner/home-assistant-chores/commit/df4c88056c6b4e6f0294ab34e0f4a25310e9e045))
* **issue-189:** make chores.snooze value/unit optional, defaulting to device config ([#191](https://github.com/jamiegardiner/home-assistant-chores/issues/191)) ([a3abbe8](https://github.com/jamiegardiner/home-assistant-chores/commit/a3abbe84d4d314f4efe7fcb6e564bd9aa823d58d))
* **issue-190:** add configurable interval unit (days/weeks) with interval_days migration ([#194](https://github.com/jamiegardiner/home-assistant-chores/issues/194)) ([47534ea](https://github.com/jamiegardiner/home-assistant-chores/commit/47534ea13b1f82a5991f7c74a93047c2e8d1a55b))
* **issue-196:** expose next_due and last_completed as extra state attributes on ChoreSensor ([#198](https://github.com/jamiegardiner/home-assistant-chores/issues/198)) ([74807c6](https://github.com/jamiegardiner/home-assistant-chores/commit/74807c652af6047ca2383fa0511018c321c8cd6d))
* **issue-208:** add chores.snooze_exact service for exact-datetime snoozing ([#209](https://github.com/jamiegardiner/home-assistant-chores/issues/209)) ([9a0e72d](https://github.com/jamiegardiner/home-assistant-chores/commit/9a0e72d257a4047d5ab8432824fa1c4747e1f31a))


### Bug Fixes

* **issue-199:** guard against None coordinator.data in diagnostics ([#210](https://github.com/jamiegardiner/home-assistant-chores/issues/210)) ([262ed9e](https://github.com/jamiegardiner/home-assistant-chores/commit/262ed9e0a50f2447af21748ba8d9d45722a91300))

## [1.1.0](https://github.com/jamiegardiner/home-assistant-chores/compare/v1.0.1...v1.1.0) (2026-06-16)


### Features

* **issue-152:** add diagnostics platform ([#178](https://github.com/jamiegardiner/home-assistant-chores/issues/178)) ([3e9c847](https://github.com/jamiegardiner/home-assistant-chores/commit/3e9c847fe16cd64016ff0c284c538e3911d5e690))
* **issue-153:** translatable exceptions via translation_key ([#175](https://github.com/jamiegardiner/home-assistant-chores/issues/175)) ([43cd87b](https://github.com/jamiegardiner/home-assistant-chores/commit/43cd87b31773cb275faf8af90ed6cbb911912680))
* **issue-154:** add icons.json for icon-translations Gold quality rule ([#167](https://github.com/jamiegardiner/home-assistant-chores/issues/167)) ([4e4b80f](https://github.com/jamiegardiner/home-assistant-chores/commit/4e4b80f2367165849731ffed58d4fcb4c2bd146c))
* **issue-155:** gracefully recover from corrupt persisted chore state ([#169](https://github.com/jamiegardiner/home-assistant-chores/issues/169)) ([efd08df](https://github.com/jamiegardiner/home-assistant-chores/commit/efd08df47419800a29ee080eebb13cac8d5602a5))
* **issue-176:** raise ServiceValidationError for snooze validation; remove unreachable entity guards ([#179](https://github.com/jamiegardiner/home-assistant-chores/issues/179)) ([41ef9b9](https://github.com/jamiegardiner/home-assistant-chores/commit/41ef9b99479838f399ac843e8336c616932eddfd))


### Bug Fixes

* **issue-159:** remove suggested_object_id override causing doubled entity_id ([#162](https://github.com/jamiegardiner/home-assistant-chores/issues/162)) ([82ece86](https://github.com/jamiegardiner/home-assistant-chores/commit/82ece86f1d4e99571c873c255658b6a63cfa5f4d))

## [1.0.1](https://github.com/jamiegardiner/home-assistant-chores/compare/v1.0.0...v1.0.1) (2026-06-15)


### Bug Fixes

* **issue-121:** persist cleared snooze_until in async_update_config when snooze has expired ([#126](https://github.com/jamiegardiner/home-assistant-chores/issues/126)) ([f716af5](https://github.com/jamiegardiner/home-assistant-chores/commit/f716af51116f1f50dc5309cb42551ff15140d993))
* **issue-136:** persist cleared snooze_until to entry.options on natural expiry ([#140](https://github.com/jamiegardiner/home-assistant-chores/issues/140)) ([fdd7b07](https://github.com/jamiegardiner/home-assistant-chores/commit/fdd7b0721014da4277f481347d9e7559598a1303))

## [1.0.0](https://github.com/jamiegardiner/home-assistant-chores/compare/v0.1.0...v1.0.0) (2026-06-14)


### Features

* add snooze state and chores.snooze service ([#15](https://github.com/jamiegardiner/home-assistant-chores/issues/15)) ([b9bc66a](https://github.com/jamiegardiner/home-assistant-chores/commit/b9bc66aa35ecedbf65180251c02e8fe82b9d5e6d))
* Chores — Home Assistant custom integration for household chore tracking ([4f6aa15](https://github.com/jamiegardiner/home-assistant-chores/commit/4f6aa1511150fbc2f2334bbd0e9b25d31cfe1d79))
* **issue-11:** add chores.unsnooze service ([#16](https://github.com/jamiegardiner/home-assistant-chores/issues/16)) ([0efb9b6](https://github.com/jamiegardiner/home-assistant-chores/commit/0efb9b603131cae95c8c35b781399a1b407b68aa))
* **issue-27:** enum device class, translatable states, None for unknown ([#60](https://github.com/jamiegardiner/home-assistant-chores/issues/60)) ([83a50d1](https://github.com/jamiegardiner/home-assistant-chores/commit/83a50d153b4dcdf8014ab836f8954b803b23ff11))
* **issue-56:** per-chore helper entries — each chore is its own config entry ([#59](https://github.com/jamiegardiner/home-assistant-chores/issues/59)) ([53734f9](https://github.com/jamiegardiner/home-assistant-chores/commit/53734f917fb2a3fe709d1c76c954a4bd31a9b45d))
* **issue-68:** device refactor — 8-entity layout, interval_days, default_snooze_days ([#69](https://github.com/jamiegardiner/home-assistant-chores/issues/69)) ([ade21a4](https://github.com/jamiegardiner/home-assistant-chores/commit/ade21a4e96cd20fd7a85205fe7a957b1f7940c32))
* **issue-70:** replace snooze service with value+unit contract; move snooze_until to datetime ([#77](https://github.com/jamiegardiner/home-assistant-chores/issues/77)) ([149a13a](https://github.com/jamiegardiner/home-assistant-chores/commit/149a13aa9953b76139721354c6c2bcf0449dd825))
* **issue-71:** replace default_snooze_days with default_snooze_value + default_snooze_unit ([#78](https://github.com/jamiegardiner/home-assistant-chores/issues/78)) ([7b5d38e](https://github.com/jamiegardiner/home-assistant-chores/commit/7b5d38e40b8edf3f36087433030d299e1540e39b))
* **issue-72:** record completion datetime; add completed_at to complete service ([#79](https://github.com/jamiegardiner/home-assistant-chores/issues/79)) ([7310701](https://github.com/jamiegardiner/home-assistant-chores/commit/73107018f0c54483f6c86330ad7237ab6e13c715))
* **issue-80:** CONFIG write-back foundation; interval & default-snooze entities ([#84](https://github.com/jamiegardiner/home-assistant-chores/issues/84)) ([678258f](https://github.com/jamiegardiner/home-assistant-chores/commit/678258f17268243cbcb3685c963e260c48e65439))
* **issue-81:** notification time CONFIG time entity ([#85](https://github.com/jamiegardiner/home-assistant-chores/issues/85)) ([266ccaf](https://github.com/jamiegardiner/home-assistant-chores/commit/266ccaf8a4e86dde3cfd14546d76fafbcfd554a1))
* **issue-82:** minimal creation flow, nullable last_completed, drop options flow ([#88](https://github.com/jamiegardiner/home-assistant-chores/issues/88)) ([6e2f1f9](https://github.com/jamiegardiner/home-assistant-chores/commit/6e2f1f9f60bd99275a0f06c6d76f4af19f19a0d0))
* **issue-95:** add PARALLEL_UPDATES = 0 to all platform modules ([#104](https://github.com/jamiegardiner/home-assistant-chores/issues/104)) ([47606fb](https://github.com/jamiegardiner/home-assistant-chores/commit/47606fb861b14f538fd85671bb084e600e7785f6))


### Bug Fixes

* **issue-22:** migrate to entity services for full target resolution ([#41](https://github.com/jamiegardiner/home-assistant-chores/issues/41)) ([28121f2](https://github.com/jamiegardiner/home-assistant-chores/commit/28121f21943f343b81b0474416ec83b1e01a7e1c))
* **issue-23:** replace slug-based chore identity with stable UUID ([#51](https://github.com/jamiegardiner/home-assistant-chores/issues/51)) ([1600f0d](https://github.com/jamiegardiner/home-assistant-chores/commit/1600f0d7de8475beeaf2060537d5b372b79f9dd0))
* **issue-24:** bump hacs.json minimum HA version to 2024.11.0 ([#38](https://github.com/jamiegardiner/home-assistant-chores/issues/38)) ([0f21048](https://github.com/jamiegardiner/home-assistant-chores/commit/0f210481724820774215b4bdb13743e51b5313b2))
* **issue-25:** delete storage file on config entry removal ([#52](https://github.com/jamiegardiner/home-assistant-chores/issues/52)) ([05146e2](https://github.com/jamiegardiner/home-assistant-chores/commit/05146e2ce7603d4e687cdb31fd681aa42634aadb))
* **issue-26:** reject non-future snooze dates in coordinator ([#55](https://github.com/jamiegardiner/home-assistant-chores/issues/55)) ([7ecae8e](https://github.com/jamiegardiner/home-assistant-chores/commit/7ecae8eb2d8e5b3de65893c7003d6a2c2f79a363))
* **issue-66:** fix mdformat exclusion for CHANGELOG.md ([#125](https://github.com/jamiegardiner/home-assistant-chores/issues/125)) ([1bd103b](https://github.com/jamiegardiner/home-assistant-chores/commit/1bd103bc18ecb703e3bc7e853923eda3412078cf))
* **issue-94:** make diagnostic sensors report unavailable instead of unknown ([#99](https://github.com/jamiegardiner/home-assistant-chores/issues/99)) ([a995372](https://github.com/jamiegardiner/home-assistant-chores/commit/a9953728d5c2b71e9bbf0c2ac48defec170f64ec))

## Changelog
