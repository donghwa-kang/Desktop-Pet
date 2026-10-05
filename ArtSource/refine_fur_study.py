"""Refine the study's lighting and compare an approximate diffuse fiber shader.

Geometry is the v01 groom. This is a studio rendering experiment, not a game shader.
"""
import argparse
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
out = root / 'ArtSource/FurStudy'
parser = argparse.ArgumentParser()
parser.add_argument('--samples', type=int, default=96)
parser.add_argument('--size', type=int, default=760)
parser.add_argument('--quick', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(out / 'ogong_fur_study_v01.blend'))
scene = bpy.context.scene
for ob in scene.objects:
    if ob.type == 'CURVES':
        radius = ob.data.attributes.get('radius')
        values = np.empty(len(radius.data), dtype=np.float32)
        radius.data.foreach_get('value', values)
        values *= 3.8 if ob.get('layer') == 'undercoat' else 2.4
        radius.data.foreach_set('value', values)
        ob['preview_radius_multiplier'] = 3.8 if ob.get('layer') == 'undercoat' else 2.4
mat = bpy.data.materials['White_Fur_Fiber']
nodes, links = mat.node_tree.nodes, mat.node_tree.links
output = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
shade = next(n for n in nodes if n.type == 'VALTORGB')
shade.color_ramp.elements[0].color = (.62, .62, .60, 1)
shade.color_ramp.elements[1].color = (.75, .75, .72, 1)
diffuse = nodes.new('ShaderNodeBsdfDiffuse')
diffuse.inputs['Roughness'].default_value = .25
links.new(shade.outputs[0], diffuse.inputs['Color'])
translucent = nodes.new('ShaderNodeBsdfTranslucent')
links.new(shade.outputs[0], translucent.inputs['Color'])
mix = nodes.new('ShaderNodeMixShader')
mix.inputs[0].default_value = .15
links.new(diffuse.outputs[0], mix.inputs[1])
links.new(translucent.outputs[0], mix.inputs[2])
links.new(mix.outputs[0], output.inputs['Surface'])
mat['description'] = 'Approximate diffuse/translucent white fiber shader; compare with v01 Hair BSDF.'
base = bpy.data.materials['Study_Base_White_Coat_With_Original_Face_Details']
mask = next(n for n in base.node_tree.nodes if n.type == 'MAP_RANGE')
mask.inputs['From Min'].default_value = .035
mask.inputs['From Max'].default_value = .12
scene.view_settings.exposure = -.45
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.cycles.samples = args.samples
scene.cycles.max_bounces = 6
scene.cycles.diffuse_bounces = 3
scene.cycles.transmission_bounces = 3
scene.cycles.adaptive_threshold = .012
scene.render.filter_size = 1.5
scene.render.resolution_x = args.size
scene.render.resolution_y = int(args.size*1.05)
scene.render.resolution_percentage = 100
target = Vector((0,-.65,.24))
cam = scene.camera

def render(name, loc, size=None):
    cam.location = loc
    cam.rotation_euler = (target-cam.location).to_track_quat('-Z','Y').to_euler()
    if size: scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.filepath = str(out / name)
    print('RENDER', name, flush=True)
    bpy.ops.render.render(write_still=True)

if args.quick:
    render('fur_v02_preview.png', (0,-2.4,.32))
else:
    bpy.data.texts['READ_ME_FUR_STUDY'].write('\nv02: approximate diffuse/translucent fibers; lower exposure; source-coat tint corrected.\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'ogong_fur_study_v02.blend'), compress=True)
    render('fur_v02_front.png', (0,-2.4,.32))
    render('fur_v02_threequarter.png', (.95,-2.3,.48))
    render('fur_v02_desktop_256.png', (0,-2.4,.32), (256,268))
print('REFINE_COMPLETE', flush=True)
