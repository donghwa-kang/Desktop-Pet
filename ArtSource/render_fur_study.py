"""Render the editable groom using Blender 5.2.2 with native OIDN denoising.

Run via the official bpy module, or Blender 5.2.2's Python runner.
The original surface/groom v01 remains available for comparison.
"""
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
out = root / 'ArtSource/FurStudy'
bpy.context.preferences.filepaths.use_scripts_auto_execute = False
bpy.ops.wm.open_mainfile(filepath=str(out / 'ogong_fur_study_v01.blend'))
scene = bpy.context.scene
scene.render.threads_mode = 'FIXED'
scene.render.threads = 6
for ob in scene.objects:
    if ob.type == 'CURVES':
        radius = ob.data.attributes.get('radius')
        values = np.empty(len(radius.data), dtype=np.float32)
        radius.data.foreach_get('value', values)
        scale = 2.4 if ob.get('layer') == 'undercoat' else 1.7
        radius.data.foreach_set('value', values*scale)
        ob['preview_radius_multiplier'] = scale
base = bpy.data.materials['Study_Base_White_Coat_With_Original_Face_Details']
mask = next(n for n in base.node_tree.nodes if n.type == 'MAP_RANGE')
mask.inputs['From Min'].default_value = .035
mask.inputs['From Max'].default_value = .12
scene.view_settings.exposure = -.6
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.cycles.denoiser = 'OPENIMAGEDENOISE'
scene.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
scene.cycles.adaptive_threshold = .015
scene.render.filter_size = 1.3
scene.render.resolution_x = 800
scene.render.resolution_y = 840
scene.render.resolution_percentage = 100
target = Vector((0,-.65,.24))
cam = scene.camera
cam.location = (0,-2.4,.32)
cam.rotation_euler = (target-cam.location).to_track_quat('-Z','Y').to_euler()
scene['study_status'] = 'Fur test on retriever reference bust. Ogong facial likeness not modeled yet.'
scene['render_revision'] = 'v03: native Hair BSDF, adjusted subpixel fiber width, Blender 5.2.2 OIDN'
bpy.data.texts['READ_ME_FUR_STUDY'].write('\nv03 render: Blender 5.2.2, native Hair BSDF, OIDN; adjusted fiber width and exposure.\n')

def render(name, location, size=(800,840)):
    cam.location = location
    cam.rotation_euler = (target-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.filepath = str(out / name)
    print('RENDER_START',name,bpy.app.version_string,flush=True)
    bpy.ops.render.render(write_still=True)
    print('RENDER_FINISHED',name,flush=True)

bpy.ops.wm.save_as_mainfile(filepath=str(out / 'ogong_fur_study_v03.blend'), compress=True)
render('fur_v03_front.png', (0,-2.4,.32))
render('fur_v03_threequarter.png', (.95,-2.3,.48))
render('fur_v03_desktop_256.png', (0,-2.4,.32), (256,268))
metadata = {
    'blender_version': bpy.app.version_string,
    'samples': scene.cycles.samples,
    'denoiser': scene.cycles.denoiser,
    'shader': 'Principled Hair BSDF / Chiang',
    'native_curve_objects': sum(o.type=='CURVES' for o in scene.objects),
    'strand_count': sum(len(o.data.curves) for o in scene.objects if o.type=='CURVES'),
    'likeness_status': 'reference retriever bust, not final Ogong likeness',
    'runtime_status': 'offline rendered study; Unity performance untested',
}
(out / 'render_v03.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
print('FUR_REVIEW_COMPLETE',json.dumps(metadata),flush=True)
