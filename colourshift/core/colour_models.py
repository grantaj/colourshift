# Auto-generated mechanical refactor from single-file version
import numpy as np
import colour

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4)]

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*(int(255*x) for x in rgb))

def rgb_to_XYZ(rgb):
    return colour.sRGB_to_XYZ(rgb)

def is_valid_JMh(J, M, h):
    return (
        np.isfinite(J) and np.isfinite(M) and np.isfinite(h) and
        0 <= J <= 100 and
        0 <= M <= 100 and
        0 <= h <= 360
    )

