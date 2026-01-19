# OpenAPI Client Generation (Android)

## Goal
Generate Android client models and API interfaces from the backend OpenAPI schema to eliminate contract drift.

## Schema
- Exported automatically via CI: `docs/openapi.json` artifact
- Manual export (dev): `make openapi`

## Approach Options
1. Use OpenAPI Generator CLI (kotlin client)
   - Group and map schemas to existing data models
   - Integrate with Gradle as a generation task
2. Use custom generator to produce DTOs only
   - Retain Retrofit interfaces manually while generating models

## Next Steps
- Evaluate `openapi-generator` with `kotlin` and `kotlin-android` templates
- Prototype generation into `android-app/generated` (ignored by VCS)
- Map generated DTOs to existing `Sneaker`, `PriceSnapshot`, and related classes
- Add Gradle task to regenerate on schema changes

## Notes
- Keep secrets out of generated code
- Validate model parity with unit tests
- Document the generation process in README / CI logs

