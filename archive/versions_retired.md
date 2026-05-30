# ConvoySIM Versions

This file tracks filesystem version snapshots for ConvoySIM.

## Version 1 - Stage A/B/C baseline snapshot

Created: 2026-05-23 04:53

Snapshot location:

```text
C:\dev\ConvoySIM_versions\v1
```

Version 1 contains the current baseline before continuing Version 2 work:

- Stage A simulation runner, CSV inputs, output CSV, log CSV, charts, and Tk GUI.
- Stage A scenario-based timestamped output naming and `convoysim.ini` run-file memory.
- Stage B explicit parameter sweep optimizer and example sweep CSV.
- Stage C first straight-line convoy visualization with playback controls, time scrubber, speed slider, legend toggle, and status styling.
- Unit tests and project documentation present at the time of the snapshot.

Snapshot exclusions:

- `.git`
- Python cache folders such as `__pycache__`
- transient test/cache folders
- `*.pyc`

### Restore Version 1

This is a filesystem restore point, not a Git checkpoint.

To return to Version 1:

1. Close any running ConvoySIM tools.
2. Move or delete the current `C:\dev\ConvoySIM` workspace.
3. Copy `C:\dev\ConvoySIM_versions\v1` back to `C:\dev\ConvoySIM`.
4. Open `C:\dev\ConvoySIM` in Cursor.
5. Run validation:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Alternative: open `C:\dev\ConvoySIM_versions\v1` directly as a separate project to inspect or run Version 1 without replacing the active workspace.

## Version 2 - Active development

Started: 2026-05-23 04:53

Active workspace:

```text
C:\dev\ConvoySIM
```

All work after the Version 1 snapshot belongs to Version 2 unless another snapshot is created.
