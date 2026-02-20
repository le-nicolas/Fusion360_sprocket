# Adjustable Drive Sprocket (Fusion 360 Add-In)

This repository contains a Fusion 360 Python add-in that generates a drive sprocket body from user inputs.

## Features

- Adjustable tooth count (integer input).
- Adjustable chain pitch, roller diameter, thickness, bore diameter, and tooth tip clearance.
- Creates a new component each run so generated sprockets are isolated in the design tree.

## Files

- `AdjustableDriveSprocket/AdjustableDriveSprocket.py`: Add-in logic.
- `AdjustableDriveSprocket/AdjustableDriveSprocket.manifest`: Fusion 360 add-in manifest.

## Install in Fusion 360

1. Open Fusion 360.
2. Go to `Utilities` -> `Add-Ins` -> `Scripts and Add-Ins`.
3. Open the `Add-Ins` tab.
4. Click `+` (or `Add Existing` depending on version).
5. Select the `AdjustableDriveSprocket` folder from this repo.
6. Run the add-in.

## Usage

1. In the `Design` workspace, open the `Create` panel.
2. Click `Adjustable Drive Sprocket`.
3. Set:
   - Tooth Count
   - Chain Pitch
   - Roller Diameter
   - Sprocket Thickness
   - Bore Diameter
   - Tip Clearance
4. Confirm to generate the sprocket.

## Publish to GitHub

If this folder is your repository root:

```powershell
git add .
git commit -m "Add Fusion 360 adjustable drive sprocket add-in"
git push origin master
```

If you want this as a new repository, create one on GitHub first and then run:

```powershell
git init
git add .
git commit -m "Initial commit: Fusion 360 adjustable drive sprocket add-in"
git branch -M main
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```
