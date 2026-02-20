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
- Adjustable chain pitch, roller diameter, thickness, tip clearance, and bores.
- Manual center distance or auto center distance from chain links.
- Creates separate drive and driven sprocket components.

Core math:

- Pitch radius: `r = p / (2 sin(pi / z))`
- Chain-length approximation for auto center:
  - `L = 2m + (z1 + z2)/2 + ((z2 - z1)^2)/(4 pi^2 m)`
  - `m = C / p`

## Add-In 2: Adjustable Chain Drive

Path:

- `AdjustableChainDrive/AdjustableChainDrive.py`
- `AdjustableChainDrive/AdjustableChainDrive.manifest`

What it does:

- Creates a chain roller loop around a drive and driven sprocket pair.
- Uses drive/driven tooth counts and chain pitch to compute pitch radii.
- Automatically accounts for sprocket center distance by:
  - reading selected drive/driven sprocket occurrences, or
  - auto-detecting components named like `Drive Sprocket` and `Driven Sprocket`.
- Supports manual center distance when selection mode is off.
- Supports auto link count or manual link count.

Notes:

- Auto link count chooses the nearest practical count and reports effective pitch deviation.
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
