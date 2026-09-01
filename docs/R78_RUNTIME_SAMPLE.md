# r78 matched-device runtime sample

Validated presentation examples for UI development.

## Idle
- active=0
- game=NA
- window_mode=INACTIVE
- user_mode=AUTO
- root authority=RESTORED

## Arcane Legends active / multiwindow
- active=1
- game=sts.al
- window_mode=MULTIWINDOW
- profile=STABLE
- Local AI state observed: MODE=OFFLINE_BASELINE, SOURCE=LOCAL_BASELINE
- network state read-only

## Gemini quota fallback
- primary reasoning HTTP state observed: 429
- Local AI remains active as fallback
- strategy formula/result may be absent because no valid Gemini proposal reached the formula pipeline
- resync state may be NEEDS_RESYNC with backoff semantics

## Teardown
- active=0
- game=NA
- window_mode=INACTIVE
- root authority=RESTORED

These samples are UI-state fixtures, not hard-coded policy values. CPU/GPU/FPS/temperature/network numbers must always come from the current runtime snapshot.
