# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody


from pathlib import Path

def _list_modules():
    """Module names in this dir, excluding __init__.py."""
    mod_dir = Path(__file__).parent
    return [
        file.stem
        for file in mod_dir.glob("*.py")
        if file.is_file() and file.name != "__init__.py"
    ]

all_modules = tuple(sorted(_list_modules()))
