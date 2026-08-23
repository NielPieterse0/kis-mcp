# Plan

1. Add a Windows PowerShell regression test that reproduces the unsupported three-argument `File.Move` receipt failure.
2. Introduce one compatible atomic receipt replacement helper using same-directory temporary files and `File.Replace` for existing targets, with two-argument `File.Move` for first creation.
3. Route both primary and fallback receipt writers through that helper.
4. Run the focused post-land restart test module and change scope check.
5. Review the exact diff, publish and land through governed KIS delivery, then live-trigger the hook and verify a fresh `kis-dev` 8011 runtime plus terminal receipt evidence.
