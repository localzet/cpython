"""Show exception presentation on the pinned base and review builds."""
import traceback

class CustomHash:
    def __hash__(self):
        exc = TypeError("custom hash failed")
        exc.add_note("inside CustomHash.__hash__")
        raise exc

def dict_custom():
    return {CustomHash(): 1}

def set_custom():
    return {CustomHash()}

def dict_builtin():
    return {[]: 1}

def set_builtin():
    return {[]}

def dict_inside_except():
    try:
        1 / 0
    except ZeroDivisionError:
        return {[]: 1}

for title, callback in [
    ("dict: Python __hash__ with a note", dict_custom),
    ("set: Python __hash__ with a note", set_custom),
    ("dict: built-in unhashable list", dict_builtin),
    ("set: built-in unhashable list", set_builtin),
    ("dict: built-in error inside except", dict_inside_except),
]:
    print(f"\n--- {title} ---", flush=True)
    try:
        callback()
    except Exception as err:
        traceback.print_exception(err)
