import adsk.core
import adsk.fusion
import traceback
import math

APP_NAME = 'Adjustable Chain Drive'
CMD_ID = 'com.lenicolas.adjustablechaindrive'
CMD_NAME = 'Adjustable Chain Drive'
CMD_DESC = 'Generate a chain loop around drive and driven sprockets with automatic center-distance handling.'
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


def _distance_2d(a, b):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    return math.sqrt((dx * dx) + (dy * dy))


def _lerp(a, b, t):
    return (a[0] + ((b[0] - a[0]) * t), a[1] + ((b[1] - a[1]) * t))


def _point_from_angle(center_xy, radius, angle):
    return (center_xy[0] + (radius * math.cos(angle)), center_xy[1] + (radius * math.sin(angle)))


def _pitch_radius(chain_pitch, tooth_count):
    return chain_pitch / (2.0 * math.sin(math.pi / float(tooth_count)))


def _get_occurrence_center(occurrence):
    transform = occurrence.transform
    offset = transform.translation
    return (offset.x, offset.y, offset.z)


def _first_occurrence_for_component(root_component, component):
    occs = root_component.allOccurrencesByComponent(component)
    if occs and occs.count > 0:
        return occs.item(0)
    return None


def _selection_to_occurrence(selection_input, root_component):
    if selection_input.selectionCount < 1:
        return None

    entity = selection_input.selection(0).entity
    occurrence = adsk.fusion.Occurrence.cast(entity)
    if occurrence:
        return occurrence

    component = adsk.fusion.Component.cast(entity)
    if component:
        return _first_occurrence_for_component(root_component, component)

    return None


def _find_default_sprocket_occurrences(root_component):
    drive_occ = None
    driven_occ = None

    all_occurrences = root_component.allOccurrences
    for i in range(all_occurrences.count):
        occurrence = all_occurrences.item(i)
        comp_name = occurrence.component.name.lower()

        if drive_occ is None and ('drive sprocket' in comp_name):
            drive_occ = occurrence

        if driven_occ is None and ('driven sprocket' in comp_name):
            driven_occ = occurrence

        if drive_occ and driven_occ:
            return drive_occ, driven_occ

    return drive_occ, driven_occ


def _compute_chain_path(c1_xy, c2_xy, r1, r2):
    center_distance = _distance_2d(c1_xy, c2_xy)
    if center_distance <= 0:
        return None

    radius_delta_ratio = (r2 - r1) / center_distance
    if radius_delta_ratio <= -1.0 or radius_delta_ratio >= 1.0:
        return None

    theta = math.atan2(c2_xy[1] - c1_xy[1], c2_xy[0] - c1_xy[0])
    beta = math.acos(radius_delta_ratio)

    angle_1_upper = theta + beta
    angle_1_lower = theta - beta
    angle_2_upper = theta + beta
    angle_2_lower = theta - beta

    p1_upper = _point_from_angle(c1_xy, r1, angle_1_upper)
    p1_lower = _point_from_angle(c1_xy, r1, angle_1_lower)
    p2_upper = _point_from_angle(c2_xy, r2, angle_2_upper)
    p2_lower = _point_from_angle(c2_xy, r2, angle_2_lower)

    upper_length = _distance_2d(p1_upper, p2_upper)
    lower_length = _distance_2d(p2_lower, p1_lower)

    arc1_delta = 2.0 * beta
    arc2_delta = (2.0 * math.pi) - arc1_delta

    arc2_length = r2 * arc2_delta
    arc1_length = r1 * arc1_delta

    total_length = upper_length + arc2_length + lower_length + arc1_length

    return {
        'center_1': c1_xy,
        'center_2': c2_xy,
        'radius_1': r1,
        'radius_2': r2,
        'angle_1_lower': angle_1_lower,
        'angle_1_upper': angle_1_upper,
        'angle_2_upper': angle_2_upper,
        'p1_upper': p1_upper,
        'p2_upper': p2_upper,
        'p2_lower': p2_lower,
        'p1_lower': p1_lower,
        'upper_length': upper_length,
        'arc2_length': arc2_length,
        'lower_length': lower_length,
        'arc1_length': arc1_length,
        'arc1_delta': arc1_delta,
        'arc2_delta': arc2_delta,
        'total_length': total_length,
        'center_distance': center_distance,
    }


def _sample_chain_points(path_data, link_count):
    points = []

    segment_1_end = path_data['upper_length']
    segment_2_end = segment_1_end + path_data['arc2_length']
    segment_3_end = segment_2_end + path_data['lower_length']

    step = path_data['total_length'] / float(link_count)

    for i in range(link_count):
        s = i * step

        if s < segment_1_end:
            t = s / path_data['upper_length']
            point_xy = _lerp(path_data['p1_upper'], path_data['p2_upper'], t)

        elif s < segment_2_end:
            arc_s = s - segment_1_end
            angle = path_data['angle_2_upper'] + (arc_s / path_data['radius_2'])
            point_xy = _point_from_angle(path_data['center_2'], path_data['radius_2'], angle)

        elif s < segment_3_end:
            line_s = s - segment_2_end
            t = line_s / path_data['lower_length']
            point_xy = _lerp(path_data['p2_lower'], path_data['p1_lower'], t)

        else:
            arc_s = s - segment_3_end
            angle = path_data['angle_1_lower'] + (arc_s / path_data['radius_1'])
            point_xy = _point_from_angle(path_data['center_1'], path_data['radius_1'], angle)

        points.append(adsk.core.Point3D.create(point_xy[0], point_xy[1], 0))

    return points, step


def _set_input_state(inputs):
    use_selected = inputs.itemById('useSelectedSprockets').value
    auto_links = inputs.itemById('autoLinkCount').value

    drive_input = adsk.core.SelectionCommandInput.cast(inputs.itemById('driveOccurrence'))
    driven_input = adsk.core.SelectionCommandInput.cast(inputs.itemById('drivenOccurrence'))
    center_input = adsk.core.ValueCommandInput.cast(inputs.itemById('manualCenterDistance'))
    link_count_input = adsk.core.IntegerSpinnerCommandInput.cast(inputs.itemById('linkCount'))

    drive_input.isEnabled = use_selected
    driven_input.isEnabled = use_selected
    center_input.isEnabled = not use_selected
    link_count_input.isEnabled = not auto_links


def _create_reference_sketch(component, path_data):
    sketch = component.sketches.add(component.xYConstructionPlane)

    center_1 = adsk.core.Point3D.create(path_data['center_1'][0], path_data['center_1'][1], 0)
    center_2 = adsk.core.Point3D.create(path_data['center_2'][0], path_data['center_2'][1], 0)

    curves = sketch.sketchCurves
    center_line = curves.sketchLines.addByTwoPoints(center_1, center_2)
    center_line.isConstruction = True

    circle_1 = curves.sketchCircles.addByCenterRadius(center_1, path_data['radius_1'])
    circle_1.isConstruction = True

    circle_2 = curves.sketchCircles.addByCenterRadius(center_2, path_data['radius_2'])
    circle_2.isConstruction = True

    upper_line = curves.sketchLines.addByTwoPoints(
        adsk.core.Point3D.create(path_data['p1_upper'][0], path_data['p1_upper'][1], 0),
        adsk.core.Point3D.create(path_data['p2_upper'][0], path_data['p2_upper'][1], 0),
    )
    upper_line.isConstruction = True

    lower_line = curves.sketchLines.addByTwoPoints(
        adsk.core.Point3D.create(path_data['p2_lower'][0], path_data['p2_lower'][1], 0),
        adsk.core.Point3D.create(path_data['p1_lower'][0], path_data['p1_lower'][1], 0),
    )
    lower_line.isConstruction = True


def _create_chain_rollers(component, chain_points, roller_radius, chain_width):
    if not chain_points:
        raise RuntimeError('No chain points were generated.')

    sketch = component.sketches.add(component.xYConstructionPlane)
    circles = sketch.sketchCurves.sketchCircles

    for point in chain_points:
        circles.addByCenterRadius(point, roller_radius)

    expected_area = math.pi * roller_radius * roller_radius
    max_area = expected_area * 2.5

    profiles = []
    for i in range(sketch.profiles.count):
        profile = sketch.profiles.item(i)
        if profile.areaProperties().area < max_area:
            profiles.append(profile)

    if not profiles:
        raise RuntimeError('Could not determine roller profiles from chain sketch.')

    extrudes = component.features.extrudeFeatures
    for i, profile in enumerate(profiles):
        extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        extrude_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(chain_width))
        extrude = extrudes.add(extrude_input)

        if extrude.bodies.count > 0:
            extrude.bodies.item(0).name = 'ChainRoller_{}'.format(i + 1)


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
            inputs.addValueInput('chainWidth', 'Chain Width', 'mm', adsk.core.ValueInput.createByString('6 mm'))

            inputs.addBoolValueInput('useSelectedSprockets', 'Use Selected Sprocket Centers', True, '', True)

            drive_occurrence_input = inputs.addSelectionInput(
                'driveOccurrence',
                'Drive Sprocket Occurrence',
                'Select the drive sprocket occurrence (optional if auto-detected by name).',
            )
            drive_occurrence_input.addSelectionFilter('Occurrences')
            drive_occurrence_input.setSelectionLimits(0, 1)

            driven_occurrence_input = inputs.addSelectionInput(
                'drivenOccurrence',
                'Driven Sprocket Occurrence',
                'Select the driven sprocket occurrence (optional if auto-detected by name).',
            )
            driven_occurrence_input.addSelectionFilter('Occurrences')
            driven_occurrence_input.setSelectionLimits(0, 1)

            inputs.addValueInput('manualCenterDistance', 'Manual Center Distance', 'mm', adsk.core.ValueInput.createByString('150 mm'))

            inputs.addBoolValueInput('autoLinkCount', 'Auto Link Count', True, '', True)
            inputs.addIntegerSpinnerCommandInput('linkCount', 'Manual Link Count', 10, 6000, 1, 120)
            inputs.addBoolValueInput('enforceEvenLinks', 'Force Even Link Count', True, '', True)

            _set_input_state(inputs)

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
            if not changed_input:
                return

            if changed_input.id in ['useSelectedSprockets', 'autoLinkCount']:
                command = adsk.core.Command.cast(event_args.firingEvent.sender)
                _set_input_state(command.commandInputs)

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

            command = adsk.core.Command.cast(args.firingEvent.sender)
            inputs = command.commandInputs

            drive_teeth = inputs.itemById('driveToothCount').value
            driven_teeth = inputs.itemById('drivenToothCount').value

            chain_pitch = inputs.itemById('chainPitch').value
            roller_diameter = inputs.itemById('rollerDiameter').value
            chain_width = inputs.itemById('chainWidth').value

            use_selected = inputs.itemById('useSelectedSprockets').value
            manual_center_distance = inputs.itemById('manualCenterDistance').value

            auto_link_count = inputs.itemById('autoLinkCount').value
            requested_link_count = inputs.itemById('linkCount').value
            enforce_even_links = inputs.itemById('enforceEvenLinks').value

            if chain_pitch <= 0 or roller_diameter <= 0 or chain_width <= 0:
                ui.messageBox('Chain pitch, roller diameter, and chain width must be positive.')
                return

            pitch_radius_1 = _pitch_radius(chain_pitch, drive_teeth)
            pitch_radius_2 = _pitch_radius(chain_pitch, driven_teeth)

            root_component = design.rootComponent

            center_1 = None
            center_2 = None
            center_source = 'manual center distance input'

            if use_selected:
                drive_selection = adsk.core.SelectionCommandInput.cast(inputs.itemById('driveOccurrence'))
                driven_selection = adsk.core.SelectionCommandInput.cast(inputs.itemById('drivenOccurrence'))

                drive_occ = _selection_to_occurrence(drive_selection, root_component)
                driven_occ = _selection_to_occurrence(driven_selection, root_component)

                if (not drive_occ) or (not driven_occ):
                    auto_drive, auto_driven = _find_default_sprocket_occurrences(root_component)
                    if not drive_occ:
                        drive_occ = auto_drive
                    if not driven_occ:
                        driven_occ = auto_driven

                if (not drive_occ) or (not driven_occ):
                    ui.messageBox(
                        'Could not find drive/driven sprocket occurrences. '
                        'Select both occurrences or disable "Use Selected Sprocket Centers".'
                    )
                    return

                center_1 = _get_occurrence_center(drive_occ)
                center_2 = _get_occurrence_center(driven_occ)
                center_source = 'selected or auto-detected sprocket occurrences'

            else:
                if manual_center_distance <= 0:
                    ui.messageBox('Manual center distance must be positive.')
                    return

                center_1 = (0.0, 0.0, 0.0)
                center_2 = (manual_center_distance, 0.0, 0.0)

            center_1_xy = (center_1[0], center_1[1])
            center_2_xy = (center_2[0], center_2[1])

            center_distance = _distance_2d(center_1_xy, center_2_xy)

            if center_distance <= (pitch_radius_1 + pitch_radius_2):
                ui.messageBox(
                    'Sprocket centers are too close for chain wrap. '
                    'Increase center distance or reduce sprocket sizes.'
                )
                return

            path_data = _compute_chain_path(center_1_xy, center_2_xy, pitch_radius_1, pitch_radius_2)
            if not path_data:
                ui.messageBox('Could not compute valid tangency for the provided sprocket geometry.')
                return

            if auto_link_count:
                estimated_links = max(10, int(round(path_data['total_length'] / chain_pitch)))
                link_count = estimated_links
            else:
                link_count = requested_link_count

            if enforce_even_links and (link_count % 2 != 0):
                link_count += 1

            if link_count < 10:
                ui.messageBox('Link count is too small to form a stable chain loop.')
                return

            chain_points, actual_pitch = _sample_chain_points(path_data, link_count)

            if len(chain_points) < 4:
                ui.messageBox('Failed to generate sufficient chain points.')
                return

            plane_z = (center_1[2] + center_2[2]) * 0.5
            z_mismatch = abs(center_1[2] - center_2[2])

            chain_transform = adsk.core.Matrix3D.create()
            chain_transform.translation = adsk.core.Vector3D.create(0, 0, plane_z)
            chain_occurrence = root_component.occurrences.addNewComponent(chain_transform)
            chain_component = chain_occurrence.component
            chain_component.name = 'Chain Drive {}T-{}T'.format(drive_teeth, driven_teeth)

            _create_reference_sketch(chain_component, path_data)
            _create_chain_rollers(chain_component, chain_points, roller_diameter / 2.0, chain_width)

            center_mm = center_distance * 10.0
            requested_pitch_mm = chain_pitch * 10.0
            actual_pitch_mm = actual_pitch * 10.0
            pitch_error_pct = abs(actual_pitch - chain_pitch) / chain_pitch * 100.0

            ui.messageBox(
                'Created chain drive.\n\n'
                'Drive teeth: {}\n'
                'Driven teeth: {}\n'
                'Center distance: {:.3f} mm\n'
                'Link count: {}\n'
                'Requested pitch: {:.3f} mm\n'
                'Effective pitch: {:.3f} mm\n'
                'Pitch deviation: {:.3f}%\n'
                'Center source: {}\n'
                'Z mismatch between sprocket centers: {:.3f} mm'.format(
                    drive_teeth,
                    driven_teeth,
                    center_mm,
                    link_count,
                    requested_pitch_mm,
                    actual_pitch_mm,
                    pitch_error_pct,
                    center_source,
                    z_mismatch * 10.0,
                )
            )

        except Exception:
            if ui:
                ui.messageBox('Chain drive generation failed:\n{}'.format(traceback.format_exc()))


class CommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        pass
