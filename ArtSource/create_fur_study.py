"""Directional white-fur study on the supplied retriever's head/chest.

This is a grooming/material test, not an Ogong likeness model or a runtime asset.
Input geometry is copied and cropped; the original GLB is not overwritten.
Run in Blender 4.3: blender -b --factory-startup --disable-autoexec -t 6
  --python ArtSource/create_fur_study.py -- --samples 64 --size 760
"""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'ArtSource' / 'FurStudy'
OUT.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument('--samples', type=int, default=64)
parser.add_argument('--size', type=int, default=760)
parser.add_argument('--density', type=float, default=1.0)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
rng = np.random.default_rng(1005)


def norm(a):
    return a / np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1e-12)


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'ReferenceAssets/retriever/source.glb'))
obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
mesh = obj.data
verts = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
mesh.vertices.foreach_get('co', verts)
verts = verts.reshape(-1, 3)
faces = np.empty(len(mesh.loops), dtype=np.int32)
mesh.loops.foreach_get('vertex_index', faces)
faces = faces.reshape(-1, 3)
uvs = np.empty(len(mesh.loops) * 2, dtype=np.float32)
mesh.uv_layers.active.data.foreach_get('uv', uvs)
uvs = uvs.reshape(-1, 3, 2)
centers = verts[faces].mean(axis=1)
keep = (centers[:, 1] < -0.32) & (centers[:, 2] > -0.15)
selected = faces[keep]
unique, inverse = np.unique(selected.reshape(-1), return_inverse=True)
v = verts[unique]
f = inverse.reshape(-1, 3)
uv = uvs[keep]
material = obj.data.materials[0]
study_mesh = bpy.data.meshes.new('ReferenceBust_Surface')
study_mesh.from_pydata(v.tolist(), [], f.tolist())
study_mesh.update()
study_mesh.uv_layers.new(name='UVMap').data.foreach_set('uv', uv.reshape(-1))
study_mesh.polygons.foreach_set('use_smooth', np.ones(len(f), dtype=bool))
bust = bpy.data.objects.new('REFERENCE_BUST_Retriever_Not_Ogong', study_mesh)
bpy.context.collection.objects.link(bust)
study_mesh.materials.append(material)
bpy.data.objects.remove(obj, do_unlink=True)
bust['purpose'] = 'Head/chest white-fur test. Retriever anatomy retained. Not final likeness.'

# Copy the supplied material and desaturate the light coat; retain dark facial
# features and the tongue. This does not repaint or overwrite the input textures.
material = material.copy()
material.name = 'Study_Base_White_Coat_With_Original_Face_Details'
study_mesh.materials[0] = material
nodes, links = material.node_tree.nodes, material.node_tree.links
principled = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
base_socket = principled.inputs['Base Color']
source_color = base_socket.links[0].from_socket
lum = nodes.new('ShaderNodeRGBToBW')
links.new(source_color, lum.inputs[0])
coat_mask = nodes.new('ShaderNodeMapRange')
links.new(lum.outputs[0], coat_mask.inputs['Value'])
coat_mask.inputs['From Min'].default_value = 0.12
coat_mask.inputs['From Max'].default_value = 0.30
coat_mask.clamp = True
# Preserve tongue/mouth within a vertex-defined region.
preserve = np.clip(((-v[:, 1] - 0.77) / 0.045), 0, 1)
preserve *= np.clip((0.345 - v[:, 2]) / 0.03, 0, 1)
attr = study_mesh.attributes.new('preserve_mouth', 'FLOAT', 'POINT')
attr.data.foreach_set('value', preserve.astype(np.float32))
attribute = nodes.new('ShaderNodeAttribute')
attribute.attribute_name = 'preserve_mouth'
inv = nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'
inv.inputs[0].default_value = 1
links.new(attribute.outputs['Fac'], inv.inputs[1])
mask = nodes.new('ShaderNodeMath'); mask.operation = 'MULTIPLY'
links.new(coat_mask.outputs['Result'], mask.inputs[0])
links.new(inv.outputs[0], mask.inputs[1])
mix = nodes.new('ShaderNodeMixRGB')
mix.blend_type = 'MIX'
links.new(mask.outputs[0], mix.inputs[0])
links.new(source_color, mix.inputs[1])
mix.inputs[2].default_value = (0.67, 0.655, 0.62, 1)
links.new(mix.outputs[0], principled.inputs['Base Color'])
for name in ['Emission Color', 'Emission Strength']:
    if name in principled.inputs:
        for link in list(principled.inputs[name].links): links.remove(link)
principled.inputs['Emission Strength'].default_value = 0

tex = source_color.node.image
pix = np.empty(tex.size[0] * tex.size[1] * 4, dtype=np.float32)
tex.pixels.foreach_get(pix)
pix = pix.reshape(tex.size[1], tex.size[0], 4)

# Area-weighted roots sampled from the actual surface, with normals interpolated
# from the mesh. Facial-feature masking uses the supplied UV/color texture.
vn = np.empty(len(study_mesh.vertices) * 3, dtype=np.float32)
study_mesh.vertices.foreach_get('normal', vn)
vn = vn.reshape(-1, 3)
tri = v[f]
areas = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1) * .5
N = int(360000 * args.density)
idx = rng.choice(len(f), size=N, p=areas / areas.sum())
ab = rng.random((N, 2)); sq = np.sqrt(ab[:, 0])
w = np.column_stack((1 - sq, sq * (1 - ab[:, 1]), sq * ab[:, 1]))
roots = np.einsum('ni,nij->nj', w, tri[idx])
normals = norm(np.einsum('ni,nij->nj', w, vn[f[idx]]))
root_uv = np.einsum('ni,nij->nj', w, uv[idx])
xy = np.clip((root_uv * [tex.size[0]-1, tex.size[1]-1]).astype(int), 0, [tex.size[0]-1, tex.size[1]-1])
rgb = pix[xy[:, 1], xy[:, 0], :3]
brightness = rgb @ np.array([.2126, .7152, .0722])
mouth = (roots[:, 1] < -.79) & (roots[:, 2] < .35)
dark_feature = (brightness < .20) & (roots[:, 2] > .24)
valid = ~mouth & ~dark_feature & (roots[:, 1] < -.37)
valid &= ~((roots[:, 2] < -.12) | ((roots[:, 1] > -.4) & (normals[:, 1] > .2)))
roots, normals, root_uv = roots[valid], normals[valid], root_uv[valid]

hair_mat = bpy.data.materials.new('White_Fur_Fiber')
hair_mat.use_nodes = True
nd, lk = hair_mat.node_tree.nodes, hair_mat.node_tree.links
nd.clear()
output = nd.new('ShaderNodeOutputMaterial')
hair = nd.new('ShaderNodeBsdfHairPrincipled')
hair.parametrization = 'COLOR'
hair.model = 'CHIANG'
hair.inputs['Color'].default_value = (.73, .72, .69, 1)
hair.inputs['Roughness'].default_value = .42
hair.inputs['Radial Roughness'].default_value = .5
if 'Random Roughness' in hair.inputs:
    hair.inputs['Random Roughness'].default_value = .10
hair_info = nd.new('ShaderNodeHairInfo')
shade = nd.new('ShaderNodeValToRGB')
shade.color_ramp.elements[0].color = (.68, .67, .64, 1)
shade.color_ramp.elements[1].color = (.76, .75, .72, 1)
lk.new(hair_info.outputs['Random'], shade.inputs[0])
lk.new(shade.outputs[0], hair.inputs['Color'])
lk.new(hair.outputs[0], output.inputs['Surface'])

groom = bpy.data.collections.new('Directional Groom - editable hair curves')
bpy.context.scene.collection.children.link(groom)
manifest = {'study': 'Directional white fur on supplied retriever reference bust',
            'not_final_likeness': True, 'seed': 1005, 'density_multiplier': args.density,
            'source_triangles_in_bust': int(len(f)), 'regions': {}}


def make_coat(name, ids, length, kind, undercoat=False):
    r, n, ru = roots[ids], normals[ids], root_uv[ids]
    count = len(r)
    if count == 0: return
    sgn = np.tanh(r[:, 0] * 22)
    if kind == 'chest':
        flow = np.column_stack((sgn * .28, np.full(count, -.08), np.full(count, -1.0)))
    elif kind == 'cheek':
        flow = np.column_stack((sgn, np.full(count, .14), np.full(count, -.3)))
    elif kind == 'forehead':
        flow = np.column_stack((sgn * .8, np.full(count, .14), np.full(count, .95)))
    else:
        flow = np.column_stack((sgn, np.full(count, -.1), np.full(count, -.35)))
    tangent = norm(flow - n * (flow * n).sum(axis=1, keepdims=True))
    lateral = norm(np.cross(n, tangent))
    lengths = length * np.clip(rng.lognormal(-.025, .22, count), .48, 1.6)
    seg = 12
    t = np.linspace(0, 1, seg, dtype=np.float32)[None, :, None]
    if undercoat:
        normal_bend, tangent_bend = .85*t-.35*t*t, .15*t+.4*t*t
    else:
        normal_bend, tangent_bend = .64*t-.30*t*t, .10*t+.82*t*t
    pts = r[:, None, :] + lengths[:, None, None] * (n[:, None, :]*normal_bend + tangent[:, None, :]*tangent_bend)
    # Neighboring fibers converge gently toward local surface guide centroids.
    cell = .011 if kind != 'chest' else .022
    _, groups = np.unique(np.floor(r/cell).astype(np.int32), axis=0, return_inverse=True)
    weights = np.bincount(groups)
    centers = np.column_stack([np.bincount(groups, weights=r[:, j])/weights for j in range(3)])
    delta = centers[groups] - r
    delta -= n * (delta*n).sum(axis=1, keepdims=True)
    pts += delta[:, None, :] * t**1.8 * (.16 if undercoat else .40)
    phase = rng.uniform(0, 2*np.pi, count)[:, None, None]
    waves = (np.sin(t*np.pi*2.1+phase)-np.sin(phase)) * t
    amplitude = .022 if kind == 'chest' else .012
    pts += lateral[:, None, :] * lengths[:, None, None] * amplitude * waves
    if kind == 'chest': pts[:, :, 2] -= lengths[:, None] * .10 * t[0, :, 0]**2
    root_radius = rng.uniform(.000050, .000082, count)
    if undercoat: root_radius *= .85
    radii = root_radius[:, None] * (.04 + .96*(1-t[0, :, 0])**.72)
    data = bpy.data.hair_curves.new(name)
    data.add_curves([seg] * count)
    data.attributes['position'].data.foreach_set('vector', pts.astype(np.float32).reshape(-1))
    data.attributes.new('radius', 'FLOAT', 'POINT').data.foreach_set('value', radii.astype(np.float32).reshape(-1))
    data.surface = bust
    data.surface_uv_map = 'UVMap'
    data.attributes.new('surface_uv_coordinate', 'FLOAT2', 'CURVE').data.foreach_set('vector', ru.astype(np.float32).reshape(-1))
    data.materials.append(hair_mat)
    ob = bpy.data.objects.new(name, data)
    groom.objects.link(ob)
    ob['flow_region'] = kind
    ob['nominal_length'] = length
    ob['layer'] = 'undercoat' if undercoat else 'outercoat'
    manifest['regions'][name] = {'strands': count, 'points_per_strand': seg, 'nominal_length_scene_units': length}
    print('GROOM', name, count, flush=True)

region_chest = roots[:, 2] < .255
region_cheek = (roots[:, 2] >= .255) & (np.abs(roots[:, 0]) > .105) & (roots[:, 2] < .50)
region_forehead = (roots[:, 2] >= .45) & ~region_cheek
region_muzzle = ~region_chest & ~region_cheek & ~region_forehead
for name, mask0, length, kind in [
    ('Cheek', region_cheek, .072, 'cheek'),
    ('Forehead', region_forehead, .064, 'forehead'),
    ('Muzzle', region_muzzle, .010, 'muzzle'),
    ('Chest', region_chest, .120, 'chest'),
]:
    ids = np.flatnonzero(mask0)
    outer = ids[::3]
    inner = np.setdiff1d(ids, outer, assume_unique=True)
    make_coat(name+'_Outer', outer, length, kind)
    make_coat(name+'_Undercoat', inner, length*.38, kind, undercoat=True)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = args.samples
scene.cycles.use_denoising = False
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = .025
scene.cycles.max_bounces = 8
scene.cycles.diffuse_bounces = 3
scene.cycles.glossy_bounces = 4
scene.cycles.transmission_bounces = 6
scene.render.resolution_x = args.size
scene.render.resolution_y = int(args.size*1.05)
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
world = bpy.data.worlds.new('Neutral Studio')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.10, .12, .16, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .35
target = Vector((0, -.65, .24))
for name, loc, power, size in [
    ('Soft Key', (-1, -1.65, 1.7), 120, 1.6),
    ('Soft Fill', (1.0, -1.0, .7), 65, 1.3),
    ('Edge Light', (.4, .15, 1.35), 170, .9),
]:
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = power; ld.shape = 'DISK'; ld.size = size
    lo = bpy.data.objects.new(name, ld); scene.collection.objects.link(lo); lo.location = loc; aim(lo, target)

camera = bpy.data.cameras.new('Fur Review Camera')
cam = bpy.data.objects.new('Fur Review Camera', camera)
scene.collection.objects.link(cam)
camera.type = 'ORTHO'; camera.ortho_scale = .96
scene.camera = cam

# Exact image inputs remain outside this self-contained review scene.
readme = bpy.data.texts.new('READ_ME_FUR_STUDY')
readme.write('WHITE FUR STUDY / Not a finished Ogong model.\n'
             'Surface: cropped user-supplied golden retriever GLB.\n'
             '8 editable native Hair Curves objects: forehead, cheeks, muzzle, chest; undercoat + outercoat.\n'
             'Original GLB unchanged. No animation/Unity optimization yet.\n'
             'Parameters and reproducible seed are in ArtSource/create_fur_study.py.\n')

def render(name, location, scale=.96, size=None):
    cam.location = location; aim(cam, target); camera.ortho_scale = scale
    if size:
        scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.filepath = str(OUT / (name+'.png'))
    print('RENDER', name, flush=True)
    bpy.ops.render.render(write_still=True)

manifest['total_strands'] = sum(x['strands'] for x in manifest['regions'].values())
manifest['blender_version'] = bpy.app.version_string
(OUT / 'fur_study_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
cam.location = (0,-2.4,.32); aim(cam,target)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'ogong_fur_study_v01.blend'), compress=True)
render('fur_front', (0,-2.4,.32))
render('fur_threequarter', (.95,-2.3,.48))
render('fur_desktop_256', (0,-2.4,.32), size=(256, 268))
print('FUR_STUDY_COMPLETE', json.dumps(manifest), flush=True)
