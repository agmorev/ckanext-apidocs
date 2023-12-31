import ckan.plugins.toolkit as tk
import ckanext.apidocs.logic.schema as schema


@tk.side_effect_free
def apidocs_get_sum(context, data_dict):
    tk.check_access(
        "apidocs_get_sum", context, data_dict)
    data, errors = tk.navl_validate(
        data_dict, schema.apidocs_get_sum(), context)

    if errors:
        raise tk.ValidationError(errors)

    return {
        "left": data["left"],
        "right": data["right"],
        "sum": data["left"] + data["right"]
    }


def get_actions():
    return {
        'apidocs_get_sum': apidocs_get_sum,
    }
