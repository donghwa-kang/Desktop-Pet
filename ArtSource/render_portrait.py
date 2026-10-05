"""Render saved portrait review cameras without rebuilding the mesh or groom."""
import argparse
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'ArtSource/PortraitStudy'
parser = argparse.ArgumentParser()
parser.add_argument('--tag', default='portrait02')
parser.add_argument('--size', type=int, default=840)
parser.add_argument('--samples', type=int, default=48)
parser.add_argument('--views', nargs='+', choices=['front', 'threequarter', 'side'],
                    default=['threequarter', 'side'])
args = parser.parse_args()
bpy.context.preferences.filepaths.use_scripts_auto_execute = False
bpy.ops.wm.open_mainfile(filepath=str(OUT / f'ogong_{args.tag}.blend'))
scene = bpy.context.scene
scene.render.resolution_x = args.size
scene.render.resolution_y = int(args.size * 1.05)
scene.render.resolution_percentage = 100
scene.render.threads_mode = 'FIXED'
scene.render.threads = 6
scene.cycles.samples = args.samples
scene.cycles.use_denoising = True
scene.cycles.denoiser = 'OPENIMAGEDENOISE'
for view in args.views:
    scene.frame_set(['front', 'threequarter', 'side'].index(view) + 1)
    scene.camera = bpy.data.objects['Review_' + view.title()]
    scene.render.filepath = str(OUT / f'{args.tag}_{view}.png')
    print('RENDER', view, flush=True)
    bpy.ops.render.render(write_still=True)
print('PORTRAIT_REVIEW_COMPLETE', flush=True)
