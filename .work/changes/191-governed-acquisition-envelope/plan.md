# Governed Acquisition Envelope Plan

1. Port only the proven acquisition/settings/test changes from historical commit `141bbe8`, after confirming every touched current file equals that commit's parent.
2. Run focused acquisition/dispatch tests and Ruff.
3. Run scope check and freeze one exact candidate head.
4. Run code-quality and API-contract reviews concurrently with GitHub Actions.
5. Merge exact head, align/clean, close #361, then activate Change 192.