"""Inspect a supplied GLB and render it without altering its mesh or materials.

Run: blender --background --factory-startup --disable-autoexec --python
     ArtSource/inspect_retriever.py -- INPUT_GLB OUTPUT_DIRECTORY
Outputs stay in OUTPUT_DIRECTORY; the input is never overwritten.
"""

import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


parser = argparse.ArgumentParser()
parser.add_argument('input', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--views', nargs='+', default=['threequarter', 'front', 'side', 'clay'])
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
args.output.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(args.input.resolve()), merge_vertices=False)
source_objects = list(bpy.context.scene.objects)
meshes = [o for o in source_objects if o.type == 'MESH']
bpy.context.view_layer.update()
corners = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
low = Vector(tuple(min(v[i] for v in corners) for i in range(3)))
high = Vector(tuple(max(v[i] for v in corners) for i in range(3)))
center = (low + high) / 2
extent = max(high - low)

report = {
    'input': args.input.name,
    'blender_version': bpy.app.version_string,
    'bounds_world': {'min': list(low), 'max': list(high)},
    'source_objects': [],
    'images': [],
    'actions': [a.name for a in bpy.data.actions],
    'preview_note': 'Source mesh, transforms and materials preserved. Studio lights and cameras added.',
}
for obj in source_objects:
    rec = {'name': obj.name, 'type': obj.type, 'modifiers': [m.type for m in obj.modifiers]}
    if obj.type == 'MESH':
        mesh = obj.data
        mesh.calc_loop_triangles()
        rec.update({
            'vertices': len(mesh.vertices), 'edges': len(mesh.edges),
            'polygons': len(mesh.polygons), 'triangles': len(mesh.loop_triangles),
            'uv_layers': [uv.name for uv in mesh.uv_layers],
            'materials': [m.name if m else None for m in mesh.materials],
            'vertex_groups': [g.name for g in obj.vertex_groups],
            'shape_keys': list(mesh.shape_keys.key_blocks.keys()) if mesh.shape_keys else [],
            'particle_systems': len(obj.particle_systems),
        })
    if obj.type == 'ARMATURE':
        rec['bones'] = [b.name for b in obj.data.bones]
    report['source_objects'].append(rec)
for img in bpy.data.images:
    report['images'].append({'name': img.name, 'size': list(img.size), 'packed': bool(img.packed_file)})
(args.output / 'inspection.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('INSPECTION_REPORT', json.dumps(report), flush=True)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = False
scene.cycles.use_adaptive_sampling = True
scene.render.resolution_x = 840
scene.render.resolution_y = 760
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.world = bpy.data.worlds.new('InspectionWorld')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.3, 0.3, 0.3, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.45

studio = bpy.data.collections.new('Inspection Studio')
scene.collection.children.link(studio)
for name, offset, power, size in [
    ('Key', (1.3, -1.5, 2), 850, 2.7),
    ('Fill', (-1.5, -0.5, 1), 450, 2.5),
    ('Rim', (0.6, 1.4, 1.8), 700, 2.1),
]:
    light = bpy.data.lights.new(name, type='AREA')
    light.energy = power
    light.shape = 'DISK'
    light.size = size
    obj = bpy.data.objects.new(name, light)
    studio.objects.link(obj)
    obj.location = center + Vector(offset) * extent
    aim(obj, center)

ground_mat = bpy.data.materials.new('Inspection Ground')
ground_mat.diffuse_color = (0.12, 0.135, 0.16, 1)
bpy.ops.mesh.primitive_plane_add(size=extent * 200, location=(center.x, center.y, low.z - extent * 0.005))
ground = bpy.context.object
ground.name = 'Inspection Ground'
ground.data.materials.append(ground_mat)
for coll in list(ground.users_collection):
    coll.objects.unlink(ground)
studio.objects.link(ground)

clay = bpy.data.materials.new('Inspection Clay')
clay.diffuse_color = (0.42, 0.45, 0.5, 1)
clay.use_nodes = True
clay.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = clay.diffuse_color
clay.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.8
camera = bpy.data.cameras.new('InspectionCamera')
cam_obj = bpy.data.objects.new('InspectionCamera', camera)
studio.objects.link(cam_obj)
camera.type = 'ORTHO'
camera.ortho_scale = extent * 1.15
scene.camera = cam_obj
angles = {
    'threequarter': (1.4, -1.8, 0.85),
    'front': (0, -2.0, 0.05),
    'side': (2.0, 0, 0.08),
    'clay': (1.4, -1.8, 0.85),
}
for view in args.views:
    cam_obj.location = center + Vector(angles[view]) * extent
    aim(cam_obj, center)
    scene.view_layers[0].material_override = clay if view == 'clay' else None
    scene.render.filepath = str((args.output / f'retriever_{view}.png').resolve())
    print('RENDERING', view, flush=True)
    bpy.ops.render.render(write_still=True)
scene.view_layers[0].material_override = None
cam_obj.location = center + Vector(angles['threequarter']) * extent
aim(cam_obj, center)
bpy.ops.object.select_all(action='DESELECT')
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str((args.output / 'retriever_inspection.blend').resolve()))
print('INSPECTION_COMPLETE', flush=True)
