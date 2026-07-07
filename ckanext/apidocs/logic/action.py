import ckan.plugins.toolkit as tk


@tk.side_effect_free
def example_get_sum(context, data_dict):
    pass


@tk.side_effect_free
def apidocs_example(context):
    print("example_get_sum called")
    return {"sum": 42}


def get_actions():
    return {
        'example_get_sum': example_get_sum,
        'apidocs_example': apidocs_example,
    }
