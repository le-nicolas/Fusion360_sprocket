# Fusion 360 Sprocket + Chain Add-Ins

This repository now contains **two Fusion 360 Python add-ins**:

1. `AdjustableDriveSprocket`: builds a drive + driven sprocket pair.
2. `AdjustableChainDrive`: builds a chain loop that automatically accounts for drive/driven sprocket center distance.

## Add-In 1: Adjustable Sprocket Pair

Path:

- `AdjustableDriveSprocket/AdjustableDriveSprocket.py`
- `AdjustableDriveSprocket/AdjustableDriveSprocket.manifest`

What it does:

- Adjustable drive and driven tooth count.
- Optional auto-tooth mode from:
  - target ratio (driven:drive),
  - max sprocket diameter,
  - min/max tooth range.
- Adjustable chain pitch, roller diameter, thickness, tip clearance, and bores.
- Manual center distance or auto center distance from chain links.
- Creates separate drive and driven sprocket components.
- Tags generated sprockets with custom Fusion attributes for robust downstream detection.
- Optional CSV summary export for basic BOM/reporting.

Core math:

- Pitch radius: `r = p / (2 sin(pi / z))`
- Chain-length approximation for auto center:
  - `L = 2m + (z1 + z2)/2 + ((z2 - z1)^2)/(4 pi^2 m)`
  - `m = C / p`

Validation and engineering checks:

- Minimum sprocket tooth count: `9`.
- Roller diameter must be less than chain pitch.
- Bore diameters are validated against computed root/hub envelope.
- Center distance warns when outside the common recommended range of `30-50` pitch lengths.
- Ratio mode warns/fails when no tooth pair can satisfy ratio + diameter + range constraints.

## Add-In 2: Adjustable Chain Drive

Path:

- `AdjustableChainDrive/AdjustableChainDrive.py`
- `AdjustableChainDrive/AdjustableChainDrive.manifest`

What it does:

- Creates a chain roller loop around a drive and driven sprocket pair.
- Uses drive/driven tooth counts and chain pitch to compute pitch radii.
- Automatically accounts for sprocket center distance by:
  - reading selected drive/driven sprocket occurrences, or
  - finding attribute-tagged sprockets created by `AdjustableDriveSprocket`, with name-based fallback.
- Supports manual center distance when selection mode is off.
- Supports auto link count or manual link count.
- Includes live in-dialog summary text that updates with current inputs.
- Optional CSV summary export for chain/BOM-style reporting.

Notes:

- Auto link count chooses the nearest practical count and reports effective pitch deviation.
- Can force even link count and explicitly reports half-link requirement status.
- Warns when center distance is outside `30-50` pitches and when computed wrap angle is low.
- Geometry is generated as roller bodies for practical layout and visualization.

## Install in Fusion 360

Install each add-in folder separately:

1. Open Fusion 360.
2. Go to `Utilities` -> `Add-Ins` -> `Scripts and Add-Ins`.
3. Open the `Add-Ins` tab.
4. Click `+` / `Add Existing`.
5. Select `AdjustableDriveSprocket` and/or `AdjustableChainDrive`.
6. Run the add-in(s).

## Recommended workflow

1. Run `Adjustable Sprocket Pair` to generate drive and driven sprockets.
2. Run `Adjustable Chain Drive` with `Use Selected Sprocket Centers` enabled.
3. Select the two sprocket occurrences to auto-place the chain at the correct distance.
