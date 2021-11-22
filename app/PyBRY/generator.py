from urllib.request import urlopen
from urllib.error import URLError
from json import loads
from pybry.constants import LBRY_API_RAW_JSON_URL
from pybry.constants import DTYPE_MAPPING
from pybry.constants import LBRYD_FPATH
from pybry.constants import __LBRYD_BASE_FPATH__


def get_lbry_api_function_docs(url=LBRY_API_RAW_JSON_URL):
    """ Scrapes the given URL to a page in JSON format to obtain the documentation for the LBRY API

    :param str url: URL to the documentation we need to obtain,
     pybry.constants.LBRY_API_RAW_JSON_URL by default
    :return: List of functions retrieved from the `url` given
    :rtype: list
    """

    try:
        # Grab the page content
        docs_page = urlopen(url)

        # Read the contents of the actual url we grabbed and decode them into UTF-8
        contents = docs_page.read().decode("utf-8")

        # Return the contents loaded as JSON
        return loads(contents)

        # If we get an exception, simply exit
    except URLError as UE:
        print(UE)

    except Exception as E:
        print(E)

    return []


def generate_method_definition(func):
    """ Generates the body for the given function

    :param dict func: dict of a JSON-Formatted function as defined by the API docs
    :return: A String containing the definition for the function as it should be written in code
    :rtype: str
    """
    indent = 4

    # initial definition
    method_definition = (" " * indent) + "def " + func["name"]

    for param in func["arguments"]:
        if '<' in param["name"]:
            param["name"] = param["name"][:param["name"].index('<')]

    # Here we just create a queue and put all the parameters
    # into the queue in the order that they were given,
    params_required = [
        param for param in func["arguments"] if param["is_required"]
    ]
    params_optional = [
        param for param in func["arguments"]
        if not param["is_required"]
    ]

    # Open the parameter definitions
    method_definition += "(self, "

    for param in params_required:
        # Put the parameter into the queue

        method_definition += param["name"]
        method_definition += ", "

    for param in params_optional:
        method_definition += param["name"]

        # Default methods not required
        method_definition += "=None, "

    # Peel off the final ", " and close off the parameter definition
    method_definition = method_definition.rstrip(", ") + "):\n"

    indent += 4

    # re-indent
    method_definition += " " * indent

    # Begin with description.

    method_definition += '"""' + func["description"]

    # re-indent
    method_definition += "\n\n" + " " * indent

    # Go through each parameter and insert description & type hint
    for param in params_required + params_optional:
        # Add the type
        if param["type"] not in DTYPE_MAPPING:
            DTYPE_MAPPING[param["type"]] = param["type"]
        method_definition += ":param " + DTYPE_MAPPING[param["type"].lower()]

        # Add the name
        method_definition += " " + param["name"] + ": "

        # Add the description
        method_definition += param["description"]

        # Add optionality & reindent
        method_definition += "\n" if param[
            "is_required"] else " (Optional)\n"

        method_definition += " " * indent

    open_index = func["returns"].find('(')
    close_index = func["returns"].find(
        ')', (open_index if open_index > -1 else 0))

    func["returns"] = func["returns"].replace("\t", " " * 4)
    return_string = func["returns"].replace("\n", "")

    if open_index < close_index and func["returns"][
                                    open_index + 1:close_index] in DTYPE_MAPPING:
        method_definition += ":rtype: " + DTYPE_MAPPING[
            func["returns"][open_index + 1:close_index]]

        func["returns"] = func["returns"].replace(
            func["returns"][open_index:close_index + 1], "")

        method_definition += "\n" + " " * indent

    method_definition += ":return: " + return_string

    for i in range(0, len(return_string) + 1, 80 - (indent + 2)):
        method_definition += return_string[i:i + (
                80 - (indent + 2))] + "\n" + " " * indent

    # Close it off & reindent
    method_definition += '"""' + "\n" + " " * indent

    # Create the params map
    params_map = "__params_map = {"

    # Save the indent
    params_indent, num_params = len(
        params_map), len(params_required) + len(params_optional)

    # Append the map to the method_definition
    method_definition += params_map

    # Go through the required parameters first
    for i, param in enumerate(params_required + params_optional):

        # append the methods to the map
        method_definition += "'" + param["name"] + "': " + param["name"]

        if not param["is_required"]:
            method_definition + " if " + param[
                "name"] + "is not None else None"

        # add commas or ending bracket if needed & reindent correctly
        method_definition += ",\n" + " " * indent + ' ' * params_indent if i + 1 < num_params else ""

    method_definition += '}\n\n' + ' ' * indent

    method_definition += "return self.make_request(SERVER_ADDRESS, '" + func["name"] + "', " \
                         + params_map.rstrip(" = {") + ", timeout=self.timeout)\n\n"

    return method_definition


def comment_write(doc, lbry_file):
    for line in doc.split("\n"):
        if line:
            lbry_file.write("# " + line + "\n")


# Currently this only supports LBRYD, as LBRYCRD's API is is nowhere to be found,
# Therefore anyone wanting to use that needs to call the functions manually.
def generate_lbryd_wrapper(url=LBRY_API_RAW_JSON_URL, read_file=__LBRYD_BASE_FPATH__, write_file=LBRYD_FPATH):
    """ Generates the actual functions for lbryd_api.py based on lbry's documentation

    :param str url: URL to the documentation we need to obtain,
     pybry.constants.LBRY_API_RAW_JSON_URL by default
    :param str read_file: This is the path to the file from which we will be reading
    :param str write_file: Path from project root to the file we'll be writing to.
     """

    functions = get_lbry_api_function_docs(url)

    # Open the actual file for appending
    with open(write_file, 'w') as lbry_file:

        def comment(doc):
            comment_write(doc, lbry_file)

        comment("This file was generated at build time using the generator function")
        comment("You may edit but do so with caution")

        with open(read_file, 'r') as template:
            header = template.read()

        lbry_file.write(header)

        for group_name in functions:
            comment("GROUP: " + group_name)
            comment(functions[group_name].get("doc", ""))

            # Iterate through all the functions we retrieved
            for func in functions[group_name].get("commands", []):
                method_definition = generate_method_definition(func)

                # Write to file
                lbry_file.write(method_definition)

    try:
        from yapf.yapflib.yapf_api import FormatFile

        # Now we should format the file using the yapf formatter
        FormatFile(write_file, in_place=True)

    except ImportError as IE:
        print("[Warning]: yapf is not installed, so the generated code will not follow an easy-to-read standard")
        print(IE)


if __name__ == '__main__':
    generate_lbryd_wrapper()