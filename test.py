from volvis import visualizer as vis

import numpy as np

v = vis()
v.bg_color = [.2,.2,.2, 0]
v.caption = "testing python volume visualizer"
v.data = np.random.rand( 16,16,16 )

v.wait()

