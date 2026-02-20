# Adjustable Sprocket Pair (Fusion 360 Add-In)

This repository contains a Fusion 360 Python add-in that generates a **drive + driven sprocket pair** from user inputs.

## Features

- Adjustable drive and driven tooth count.
- Adjustable chain pitch, roller diameter, thickness, and tip clearance.
- Separate bore diameter inputs for drive and driven sprockets.
- Manual center distance input.
- Optional automatic center distance from chain link count.
- Creates two separate components (drive at origin, driven offset on +X).

## Ratio and Sizing Math

Sprocket sizing is derived from chain pitch and tooth count:

- Pitch radius: `r = p / (2 sin(pi / z))`
- Larger tooth count -> larger pitch diameter

Auto center distance uses the standard chain length approximation:

- `L = 2m + (z1 + z2)/2 + ((z2 - z1)^2)/(4 pi^2 m)`
- `m = C / p`

Where:
- `L` = chain links (pitches)
- `C` = center distance
- `p` = chain pitch
- `z1`, `z2` = drive/driven teeth

## Files

- `AdjustableDriveSprocket/AdjustableDriveSprocket.py`: Add-in logic.
- `AdjustableDriveSprocket/AdjustableDriveSprocket.manifest`: Fusion 360 add-in manifest.

## Install in Fusion 360

1. Open Fusion 360.
2. Go to `Utilities` -> `Add-Ins` -> `Scripts and Add-Ins`.
3. Open the `Add-Ins` tab.
4. Click `+` (or `Add Existing`, depending on version).
5. Select the `AdjustableDriveSprocket` folder from this repo.
6. Run the add-in.

## Usage

1. In the `Design` workspace, open the `Create` panel.
2. Click `Adjustable Sprocket Pair`.
3. Set:
   - Drive Tooth Count
   - Driven Tooth Count
   - Chain Pitch
   - Roller Diameter
   - Sprocket Thickness
   - Drive Bore Diameter
   - Driven Bore Diameter
   - Tip Clearance
4. Choose center-distance mode:
   - Auto from Chain Links
   - Manual Center Distance
5. Confirm to generate the pair.

## Notes

- This add-in creates a practical parametric sprocket profile for CAD workflow.
- For strict ANSI/ISO manufacturing-grade tooth form, use dedicated standards data for your chain class.
