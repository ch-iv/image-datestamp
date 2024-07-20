from timestamp import DateStampPosition


color_map = {
    "red": (255, 0, 0, 255),
    "blue": (0, 255, 0, 255),
    "black": (0, 0, 0, 255),
    "white": (255, 255, 255, 255),
    "old-yellow": (255, 239, 120, 255),
}

position_map = {
    "sw": DateStampPosition.SOUTH_WEST,
    "se": DateStampPosition.SOUTH_EAST,
    "nw": DateStampPosition.NORTH_WEST,
    "ne": DateStampPosition.NORTH_EAST,
}

font_map = {"News Gothic Condensed Regular": None}

scale_map = {"0.1": 0.1, "0.05": 0.05, "0.03": 0.03, "0.01": 0.01}


def parse_form(form: dict) -> dict:
    try:
        return {
            "color": color_map[form.get("color")],
            "font_path": font_map[form.get("font")],
            "font_scaling_factor": scale_map[form.get("scale")],
            "position": position_map[form.get("position")],
        }
    except ValueError:
        return {}
