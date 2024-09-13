from data import texts
from loguru import logger


def get_supply_name(boxTypeID):
    """Возвращает название типа поставки по ID."""
    if not boxTypeID:
        return 'Unknown Type'

    boxTypeIDs = boxTypeID.split(',')
    supply_names = []

    for box_id in boxTypeIDs:
        try:
            boxTypeID_int = int(box_id)
        except ValueError:
            return 'Unknown Type'

        found = False
        for name, (_, type_id) in texts.types_map.items():
            if type_id == boxTypeID_int:
                supply_names.append(name)
                found = True
                break

        if not found:
            supply_names.append('Unknown Type')

    return ', '.join(supply_names)

