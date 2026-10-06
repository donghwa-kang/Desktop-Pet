"""Render review cameras from a saved full-body scene without rebuilding it."""
import argparse
from pathlib import Path
import bpy

out=Path(__file__).resolve().parent/'FullbodyStudy'
p=argparse.ArgumentParser();p.add_argument('--tag',default='fullbody05');p.add_argument('--size',type=int,default=840);p.add_argument('--samples',type=int,default=36);p.add_argument('--views',nargs='+',default=['Front','Side','Threequarter']);a=p.parse_args()
bpy.context.preferences.filepaths.use_scripts_auto_execute=False
bpy.ops.wm.open_mainfile(filepath=str(out/f'ogong_{a.tag}.blend'))
scene=bpy.context.scene;scene.render.resolution_x=a.size;scene.render.resolution_y=a.size
scene.cycles.samples=a.samples;scene.cycles.adaptive_threshold=.035
scene.render.threads_mode='FIXED';scene.render.threads=6
for view in a.views:
    scene.frame_set(['Front','Side','Back','Top','Threequarter','Face','Opposite'].index(view)+1)
    scene.camera=bpy.data.objects['Review_'+view]
    scene.render.filepath=str(out/f'{a.tag}_{view.lower()}.png')
    print('RENDER',view,flush=True);bpy.ops.render.render(write_still=True)
print('FULLBODY_REVIEW_COMPLETE',flush=True)
