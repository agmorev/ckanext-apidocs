
def apidocs_hello():
    return "Hello, apidocs!"


def get_helpers():
    return {
        "apidocs_hello": apidocs_hello,
    }
