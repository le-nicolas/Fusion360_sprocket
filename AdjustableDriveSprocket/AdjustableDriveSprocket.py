import adsk.core
import adsk.fusion
import traceback
import math

APP_NAME = 'Adjustable Drive/Driven Sprocket Pair'
CMD_ID = 'com.lenicolas.adjustabledrivesprocket'
CMD_NAME = 'Adjustable Sprocket Pair'
CMD_DESC = 'Create drive and driven sprockets with adjustable tooth counts and chain geometry.'
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


def _sprocket_radii(tooth_count, chain_pitch, roller_diameter, tip_clearance):
    pitch_radius = chain_pitch / (2.0 * math.sin(math.pi / tooth_count))
    root_radius = pitch_radius - (0.55 * roller_diameter)
    tip_radius = pitch_radius + (0.55 * roller_diameter) + tip_clearance
    return pitch_radius, root_radius, tip_radius


def _center_distance_from_chain_links(chain_links, drive_teeth, driven_teeth, chain_pitch):
    # Standard approximate chain-length relationship:
    # L = 2m + (z1+z2)/2 + ((z2-z1)^2)/(4*pi^2*m), where m = C/p
    avg_teeth = (drive_teeth + driven_teeth) / 2.0
    tooth_delta_term = ((driven_teeth - drive_teeth) ** 2) / (4.0 * math.pi * math.pi)
    discriminant = ((chain_links - avg_teeth) ** 2) - (8.0 * tooth_delta_term)

    if discriminant < 0:
        return None

    sqrt_disc = math.sqrt(discriminant)
    m1 = ((chain_links - avg_teeth) + sqrt_disc) / 4.0
    m2 = ((chain_links - avg_teeth) - sqrt_disc) / 4.0

    m = max(m1, m2)
    if m <= 0:
        return None

    return m * chain_pitch


def _set_center_input_state(inputs):
    auto_center = inputs.itemById('autoCenter').value
    chain_links_input = adsk.core.IntegerSpinnerCommandInput.cast(inputs.itemById('chainLinks'))
    center_distance_input = adsk.core.ValueCommandInput.cast(inputs.itemById('centerDistance'))

    chain_links_input.isEnabled = auto_center
    center_distance_input.isEnabled = not auto_center


def _create_sprocket_geometry(component, tooth_count, root_radius, tip_radius, thickness, bore_diameter, body_name):
    sketches = component.sketches
    extrudes = component.features.extrudeFeatures
    patterns = component.features.circularPatternFeatures

    base_sketch = sketches.add(component.xYConstructionPlane)
    center = adsk.core.Point3D.create(0, 0, 0)
    base_sketch.sketchCurves.sketchCircles.addByCenterRadius(center, root_radius)
    if bore_diameter > 0:
        base_sketch.sketchCurves.sketchCircles.addByCenterRadius(center, bore_diameter / 2.0)

    base_profile = _largest_profile(base_sketch)
    if not base_profile:
        raise RuntimeError('Could not find a valid base profile.')

    base_extrude_input = extrudes.createInput(base_profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    base_extrude_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(thickness))
    base_extrude = extrudes.add(base_extrude_input)

    tooth_sketch = sketches.add(component.xYConstructionPlane)
    pitch_angle = (2.0 * math.pi) / tooth_count
    root_half_angle = pitch_angle * 0.22
    tip_half_angle = pitch_angle * 0.12

    p1 = _polar_point(root_radius, -root_half_angle)
    p2 = _polar_point(tip_radius, -tip_half_angle)
    p3 = _polar_point(tip_radius, tip_half_angle)
    p4 = _polar_point(root_radius, tip_half_angle)

    lines = tooth_sketch.sketchCurves.sketchLines
    lines.addByTwoPoints(p1, p2)
    lines.addByTwoPoints(p2, p3)
    lines.addByTwoPoints(p3, p4)
    lines.addByTwoPoints(p4, p1)

    tooth_profile = _largest_profile(tooth_sketch)
    if not tooth_profile:
        raise RuntimeError('Could not find a valid tooth profile.')

    tooth_extrude_input = extrudes.createInput(tooth_profile, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    tooth_extrude_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(thickness))
    tooth_extrude = extrudes.add(tooth_extrude_input)

    feature_collection = adsk.core.ObjectCollection.create()
    feature_collection.add(tooth_extrude)

    pattern_input = patterns.createInput(feature_collection, component.zConstructionAxis)
    pattern_input.quantity = adsk.core.ValueInput.createByString(str(tooth_count))
    pattern_input.totalAngle = adsk.core.ValueInput.createByString('360 deg')
    patterns.add(pattern_input)

    if base_extrude.bodies.count > 0:
        base_extrude.bodies.item(0).name = body_name


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        app = adsk.core.Application.get()
        ui = app.userInterface

        try:
            command = adsk.core.Command.cast(args.command)
            inputs = command.commandInputs

            inputs.addIntegerSpinnerCommandInput('driveToothCount', 'Drive Tooth Count', 6, 240, 1, 24)
            inputs.addIntegerSpinnerCommandInput('drivenToothCount', 'Driven Tooth Count', 6, 240, 1, 48)

            inputs.addValueInput('chainPitch', 'Chain Pitch', 'mm', adsk.core.ValueInput.createByString('12.7 mm'))
            inputs.addValueInput('rollerDiameter', 'Roller Diameter', 'mm', adsk.core.ValueInput.createByString('7.9 mm'))
            inputs.addValueInput('thickness', 'Sprocket Thickness', 'mm', adsk.core.ValueInput.createByString('6 mm'))
            inputs.addValueInput('driveBoreDiameter', 'Drive Bore Diameter', 'mm', adsk.core.ValueInput.createByString('8 mm'))
            inputs.addValueInput('drivenBoreDiameter', 'Driven Bore Diameter', 'mm', adsk.core.ValueInput.createByString('8 mm'))
            inputs.addValueInput('tipClearance', 'Tip Clearance', 'mm', adsk.core.ValueInput.createByString('1.5 mm'))

            inputs.addBoolValueInput('autoCenter', 'Auto Center Distance From Chain Links', True, '', True)
            inputs.addIntegerSpinnerCommandInput('chainLinks', 'Chain Links (pitches)', 20, 2000, 1, 120)
            inputs.addValueInput('centerDistance', 'Manual Center Distance', 'mm', adsk.core.ValueInput.createByString('150 mm'))

            _set_center_input_state(inputs)

            on_input_changed = CommandInputChangedHandler()
            command.inputChanged.add(on_input_changed)
            handlers.append(on_input_changed)

            on_execute = CommandExecuteHandler()
            command.execute.add(on_execute)
            handlers.append(on_execute)

            on_destroy = CommandDestroyHandler()
            command.destroy.add(on_destroy)
            handlers.append(on_destroy)

        except Exception:
            if ui:
                ui.messageBox('Command creation failed:\n{}'.format(traceback.format_exc()))


class CommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        app = adsk.core.Application.get()
        ui = app.userInterface

        try:
            event_args = adsk.core.InputChangedEventArgs.cast(args)
            changed_input = event_args.input
            if changed_input and changed_input.id == 'autoCenter':
                command = adsk.core.Command.cast(event_args.firingEvent.sender)
                _set_center_input_state(command.commandInputs)

        except Exception:
            if ui:
                ui.messageBox('Input change handling failed:\n{}'.format(traceback.format_exc()))


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

            event_args = adsk.core.CommandEventArgs.cast(args)
            command = event_args.command
            inputs = command.commandInputs

            drive_teeth = inputs.itemById('driveToothCount').value
            driven_teeth = inputs.itemById('drivenToothCount').value
            chain_pitch = inputs.itemById('chainPitch').value
            roller_diameter = inputs.itemById('rollerDiameter').value
            thickness = inputs.itemById('thickness').value
            drive_bore_diameter = inputs.itemById('driveBoreDiameter').value
            driven_bore_diameter = inputs.itemById('drivenBoreDiameter').value
            tip_clearance = inputs.itemById('tipClearance').value

            auto_center = inputs.itemById('autoCenter').value
            chain_links = inputs.itemById('chainLinks').value
            manual_center_distance = inputs.itemById('centerDistance').value

            if chain_pitch <= 0 or roller_diameter <= 0 or thickness <= 0:
                ui.messageBox('Chain pitch, roller diameter, and thickness must be positive.')
                return

            if drive_bore_diameter < 0 or driven_bore_diameter < 0:
                ui.messageBox('Bore diameters cannot be negative.')
                return

            drive_pitch_radius, drive_root_radius, drive_tip_radius = _sprocket_radii(
                drive_teeth, chain_pitch, roller_diameter, tip_clearance
            )
            _, driven_root_radius, driven_tip_radius = _sprocket_radii(
                driven_teeth, chain_pitch, roller_diameter, tip_clearance
            )

            if drive_root_radius <= 0 or driven_root_radius <= 0:
                ui.messageBox('Computed root radius is invalid. Increase pitch or reduce roller diameter.')
                return

            if drive_bore_diameter > (2.0 * drive_root_radius * 0.95):
                ui.messageBox('Drive bore diameter is too large for the drive sprocket root diameter.')
                return

            if driven_bore_diameter > (2.0 * driven_root_radius * 0.95):
                ui.messageBox('Driven bore diameter is too large for the driven sprocket root diameter.')
                return

            if auto_center:
                center_distance = _center_distance_from_chain_links(
                    chain_links, drive_teeth, driven_teeth, chain_pitch
                )
                if center_distance is None:
                    ui.messageBox(
                        'Chain links value is not feasible for this tooth pair. '
                        'Increase chain links or reduce tooth difference.'
                    )
                    return
            else:
                center_distance = manual_center_distance
                if center_distance <= 0:
                    ui.messageBox('Manual center distance must be positive.')
                    return

            if center_distance <= (drive_tip_radius + driven_tip_radius):
                ui.messageBox(
                    'Center distance is too small and causes sprocket overlap. '
                    'Increase center distance or use more chain links.'
                )
                return

            root_comp = design.rootComponent

            drive_occ = root_comp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            drive_comp = drive_occ.component
            drive_comp.name = '{}T Drive Sprocket'.format(drive_teeth)

            _create_sprocket_geometry(
                drive_comp,
                drive_teeth,
                drive_root_radius,
                drive_tip_radius,
                thickness,
                drive_bore_diameter,
                '{}T_Drive_Sprocket_Body'.format(drive_teeth),
            )

            driven_transform = adsk.core.Matrix3D.create()
            driven_transform.translation = adsk.core.Vector3D.create(center_distance, 0, 0)
            driven_occ = root_comp.occurrences.addNewComponent(driven_transform)
            driven_comp = driven_occ.component
            driven_comp.name = '{}T Driven Sprocket'.format(driven_teeth)

            _create_sprocket_geometry(
                driven_comp,
                driven_teeth,
                driven_root_radius,
                driven_tip_radius,
                thickness,
                driven_bore_diameter,
                '{}T_Driven_Sprocket_Body'.format(driven_teeth),
            )

            ratio = float(driven_teeth) / float(drive_teeth)
            speed_factor = float(drive_teeth) / float(driven_teeth)
            center_mm = center_distance * 10.0
            ui.messageBox(
                'Created sprocket pair.\n\n'
                'Drive teeth: {}\n'
                'Driven teeth: {}\n'
                'Ratio (driven:drive): {:.4f}\n'
                'Driven speed factor: {:.4f}x drive speed\n'
                'Center distance: {:.3f} mm'.format(
                    drive_teeth,
                    driven_teeth,
                    ratio,
                    speed_factor,
                    center_mm,
                )
            )

        except Exception:
            if ui:
                ui.messageBox('Sprocket pair generation failed:\n{}'.format(traceback.format_exc()))


class CommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        # No explicit termination needed for add-ins.
        pass
