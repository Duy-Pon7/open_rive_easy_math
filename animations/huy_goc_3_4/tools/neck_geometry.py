"""Separate the turning jaw from a stationary, rounded shirt neckline."""
from svgpathtools import Path, CubicBezier, Line, parse_path

BACKING_PATH = 'M112 236 L153 236 L153 268 L130 276 L110 260 Z'
COLLAR_UNDERLAP_PATH = 'M103 258 L165 258 L170 270 L153 299 L143 291 L105 273 L99 262 Z'


def split_neck(original):
    segments = list(parse_path(original))
    jaw_right = segments[22].start
    jaw_left = segments[32].end
    assert abs(jaw_right - complex(157.376, 247.832)) < .01
    assert abs(jaw_left - complex(105.553, 242.570)) < .01
    jaw = CubicBezier(jaw_right, complex(140, 250), complex(121, 247), jaw_left)
    head = Path(*(segments[:22] + [jaw] + segments[33:]))
    # Replace the thin skin spike down the shirt seam with a rounded base.
    rounded = CubicBezier(segments[26].end, complex(149.5, 286.8),
                          complex(147.5, 286.7), segments[28].end)
    outline = segments[22:27] + [rounded] + segments[29:33]
    neck = Path(*(outline + [Line(jaw_left, complex(106, 230)),
                             Line(complex(106, 230), complex(157, 230)),
                             Line(complex(157, 230), jaw_right)]))
    return head.d(), neck.d()
