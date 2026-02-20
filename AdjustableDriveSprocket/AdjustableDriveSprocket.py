import adsk.core
import adsk.fusion
import traceback
import math

APP_NAME = 'Adjustable Drive Sprocket'
CMD_ID = 'com.lenicolas.adjustabledrivesprocket'
CMD_NAME = 'Adjustable Drive Sprocket'
CMD_DESC = 'Create a drive sprocket with an adjustable number of teeth and key dimensions.'
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'

handlers = []


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface

    try:
        command_def = ui.commandDefinitions.itemById(CMD_ID)
        if not command_def:
            command_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_DESC)

        on_command_created = CommandCreatedHandler()
        command_def.commandCreated.add(on_command_created)
        handlers.append(on_command_created)

        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        panel = workspace.toolbarPanels.itemById(PANEL_ID)
        control = panel.controls.itemById(CMD_ID)
        if not control:
            control = panel.controls.addCommand(command_def)

        control.isPromoted = True
        control.isPromotedByDefault = True

    except Exception:
        if ui:
            ui.messageBox('Add-in start failed:\n{}'.format(traceback.format_exc()))


def stop(context):
    app = adsk.core.Application.get()
    ui = app.userInterface

    try:
        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        panel = workspace.toolbarPanels.itemById(PANEL_ID)
        control = panel.controls.itemById(CMD_ID)
        if control:
            control.deleteMe()

        command_def = ui.commandDefinitions.itemById(CMD_ID)
        if command_def:
            command_def.deleteMe()

    except Exception:
        if ui:
            ui.messageBox('Add-in stop failed:\n{}'.format(traceback.format_exc()))


def _largest_profile(sketch):
    largest = None
    largest_area = -1.0

    for i in range(sketch.profiles.count):
        profile = sketch.profiles.item(i)
        area = profile.areaProperties().area
        if area > largest_area:
            largest_area = area
            largest = profile

    return largest


def _polar_point(radius, angle_rad):
    return adsk.core.Point3D.create(radius * math.cos(angle_rad), radius * math.sin(angle_rad), 0)


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        app = adsk.core.Application.get()
        ui = app.userInterface

        try:
            command = adsk.core.Command.cast(args.command)
            inputs = command.commandInputs

            inputs.addIntegerSpinnerCommandInput('toothCount', 'Tooth Count', 6, 240, 1, 24)
            inputs.addValueInput('chainPitch', 'Chain Pitch', 'mm', adsk.core.ValueInput.createByString('12.7 mm'))
            inputs.addValueInput('rollerDiameter', 'Roller Diameter', 'mm', adsk.core.ValueInput.createByString('7.9 mm'))
            inputs.addValueInput('thickness', 'Sprocket Thickness', 'mm', adsk.core.ValueInput.createByString('6 mm'))
            inputs.addValueInput('boreDiameter', 'Bore Diameter', 'mm', adsk.core.ValueInput.createByString('8 mm'))
            inputs.addValueInput('tipClearance', 'Tip Clearance', 'mm', adsk.core.ValueInput.createByString('1.5 mm'))

            on_execute = CommandExecuteHandler()
            command.execute.add(on_execute)
            handlers.append(on_execute)

            on_destroy = CommandDestroyHandler()
            command.destroy.add(on_destroy)
            handlers.append(on_destroy)

        except Exception:
            if ui:
                ui.messageBox('Command creation failed:\n{}'.format(traceback.format_exc()))


class CommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        app = adsk.core.Application.get()
        ui = app.userInterface

        try:
            design = adsk.fusion.Design.cast(app.activeProduct)
            if not design:
                ui.messageBox('An active Fusion 360 design is required.')
                return

            command = adsk.core.Command.cast(args.firingEvent.sender)
            inputs = command.commandInputs

            tooth_count = inputs.itemById('toothCount').value
            chain_pitch = inputs.itemById('chainPitch').value
            roller_diameter = inputs.itemById('rollerDiameter').value
            thickness = inputs.itemById('thickness').value
            bore_diameter = inputs.itemById('boreDiameter').value
            tip_clearance = inputs.itemById('tipClearance').value

            if chain_pitch <= 0 or roller_diameter <= 0 or thickness <= 0:
                ui.messageBox('Chain pitch, roller diameter, and thickness must be positive.')
                return

            if bore_diameter < 0:
                ui.messageBox('Bore diameter cannot be negative.')
                return

            pitch_radius = chain_pitch / (2.0 * math.sin(math.pi / tooth_count))
            root_radius = pitch_radius - (0.55 * roller_diameter)
            tip_radius = pitch_radius + (0.55 * roller_diameter) + tip_clearance

            if root_radius <= 0:
                ui.messageBox('Computed root radius is invalid. Increase pitch or reduce roller diameter.')
                return

            if tip_radius <= root_radius:
                ui.messageBox('Tip radius must be larger than root radius. Adjust dimensions.')
                return

            if bore_diameter > (2.0 * root_radius * 0.95):
                ui.messageBox('Bore diameter is too large for the computed sprocket root diameter.')
                return

            root_comp = design.rootComponent
            occ = root_comp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            sprocket_comp = occ.component
            sprocket_comp.name = '{}T Sprocket'.format(tooth_count)

            sketches = sprocket_comp.sketches
            extrudes = sprocket_comp.features.extrudeFeatures
            patterns = sprocket_comp.features.circularPatternFeatures

            # Base body
            base_sketch = sketches.add(sprocket_comp.xYConstructionPlane)
            center = adsk.core.Point3D.create(0, 0, 0)
            base_sketch.sketchCurves.sketchCircles.addByCenterRadius(center, root_radius)
            if bore_diameter > 0:
                base_sketch.sketchCurves.sketchCircles.addByCenterRadius(center, bore_diameter / 2.0)

            base_profile = _largest_profile(base_sketch)
            if not base_profile:
                ui.messageBox('Could not find a valid base profile.')
                return

            base_extrude_input = extrudes.createInput(base_profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            base_extrude_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(thickness))
            base_extrude = extrudes.add(base_extrude_input)

            # One tooth feature
            tooth_sketch = sketches.add(sprocket_comp.xYConstructionPlane)
            pitch_angle = (2.0 * math.pi) / tooth_count
            root_half_angle = pitch_angle * 0.22
            tip_half_angle = pitch_angle * 0.12

            p1 = _polar_point(root_radius, -root_half_angle)
            p2 = _polar_point(tip_radius, -tip_half_angle)
            p3 = _polar_point(tip_radius, tip_half_angle)
            p4 = _polar_point(root_radius, tip_half_angle)

            lines = tooth_sketch.sketchCurves.sketchLines
            l1 = lines.addByTwoPoints(p1, p2)
            l2 = lines.addByTwoPoints(p2, p3)
            l3 = lines.addByTwoPoints(p3, p4)
            l4 = lines.addByTwoPoints(p4, p1)
            l1.isConstruction = False
            l2.isConstruction = False
            l3.isConstruction = False
            l4.isConstruction = False

            tooth_profile = _largest_profile(tooth_sketch)
            if not tooth_profile:
                ui.messageBox('Could not find a valid tooth profile.')
                return

            tooth_extrude_input = extrudes.createInput(tooth_profile, adsk.fusion.FeatureOperations.JoinFeatureOperation)
            tooth_extrude_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(thickness))
            tooth_extrude = extrudes.add(tooth_extrude_input)

            # Circularly pattern tooth feature
            feature_collection = adsk.core.ObjectCollection.create()
            feature_collection.add(tooth_extrude)

            pattern_input = patterns.createInput(feature_collection, sprocket_comp.zConstructionAxis)
            pattern_input.quantity = adsk.core.ValueInput.createByString(str(tooth_count))
            pattern_input.totalAngle = adsk.core.ValueInput.createByString('360 deg')
            patterns.add(pattern_input)

            # Rename resulting body for clarity
            if base_extrude.bodies.count > 0:
                base_extrude.bodies.item(0).name = '{}T_Sprocket_Body'.format(tooth_count)

        except Exception:
            if ui:
                ui.messageBox('Sprocket generation failed:\n{}'.format(traceback.format_exc()))


class CommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        # No explicit termination needed for add-ins.
        pass
