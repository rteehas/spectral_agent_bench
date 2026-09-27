import numpy as np,json,hashlib,argparse
from PIL import Image
from scipy.signal import savgol_filter
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
parser=argparse.ArgumentParser(description='Calibrate a renderer only against isolated strokes in the published Figure 5.')
parser.add_argument('--figure',required=True)
parser.add_argument('--out',required=True)
parser.add_argument('--holdout',action='store_true')
args=parser.parse_args()
path=args.figure
im=np.asarray(Image.open(path),float)
box=[1340,190,1460,390] if args.holdout else [1230,140,1350,240]
x0,y0,x1,y1=box
ref=im[y0:y1,x0:x1]
z=255-ref[:,:,1]; yy=np.arange(y1-y0)
center=(z*yy[:,None]).sum(axis=0)/z.sum(axis=0)
# Smooth only subpixel noise; no candidate coordinates are read.
center=savgol_filter(center,5,2)
fig=Figure(figsize=((x1-x0)/100,(y1-y0)/100),dpi=100);canvas=FigureCanvasAgg(fig)
ax=fig.add_axes([0,0,1,1]);ax.set_axis_off();ax.set_xlim(-.5,119.5);ax.set_ylim(y1-y0-.5,-.5)
line,=ax.plot(np.arange(120),center,color='#e41a1c',alpha=.015,lw=.72,solid_capstyle='round')
results=[]
for alpha in np.arange(.005,.0251,.0005):
 for width in np.arange(.5,3.001,.05):
  line.set_alpha(alpha);line.set_linewidth(width*.72);canvas.draw();a=np.asarray(canvas.buffer_rgba())[:,:,:3].astype(float)
  # Leave x-boundaries out because the source curve continues beyond this crop.
  err=a[:,5:-5]-ref[:,5:-5]
  results.append({'alpha':float(alpha),'width_source_pixels':float(width),'source_rgb_rmse':float(np.sqrt(np.mean(err**2)))})
results.sort(key=lambda r:r['source_rgb_rmse'])
record={'source_figure_sha256':hashlib.sha256(open(path,'rb').read()).hexdigest(),'source_only':True,
 'candidate_read':False,'crop_box_source_pixels':box,'legend_integrated_width_pixels':2.6200873362445414,
 'caveat':'Stroke coordinates estimated from source raster weighted centerline; subpixel positions/antialiasing and line opacity are not uniquely identified. Grid assesses raster representation, not scientific correctness.',
 'best':results[:20], 'frozen_renderer_result':next(r for r in results if abs(r['alpha']-.015)<1e-8 and abs(r['width_source_pixels']-1)<1e-8)}
open(args.out,'w').write(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
