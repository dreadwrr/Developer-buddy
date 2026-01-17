#!/usr/bin/env python3
import os
import tomllib
import shlex
import sys
from pyfunctions import lcl_config
from pyfunctions import get_wdir
from pyfunctions import setup_logger


def get_exports():
    if len(sys.argv) < 2:
        print("Usage: get_exports.py <username>", file=sys.stderr)
        sys.exit(1)
    user = sys.argv[1]

    xdg = os.environ.get("XDG_CONFIG_HOME")

    appdata_local = get_wdir()  # software install aka workdir

    toml_file, _, _, _ = lcl_config(user, appdata_local)
    with open(toml_file, "rb") as f:
        config = tomllib.load(f)

    ll_level = config['search']['logLEVEL']
    setup_logger(ll_level, "EXPORTS", appdata_local)

    # to /usr/local/bin/recentchanges
    nested_sections = {
        'email': ['backend'],
        'dspEDITOR': ['display'],
        'dspPATH': ['display']
    }

    for key_name, parent_sections in nested_sections.items():
        for section in parent_sections:
            value = config.get(section, {}).get(key_name)
            if value is not None:
                val = str(value).lower() if isinstance(value, bool) else str(value)
                print(f'export {key_name}={shlex.quote(val)}')

    # all
    # flatten_sections = ['backend', 'logs', 'search', 'analytics', 'display', 'diagnostics', 'paths']
    #
    # for section in flatten_sections:
    #    section_data = config.get(section, {})
    #    for k, v in section_data.items():
    #        val = str(v).lower() if isinstance(v, bool) else str(v)
    #        print(f'export {k}={shlex.quote(val)}')

    xdg = os.environ.get("XDG_CONFIG_HOME", "")

    export_a = {
        "lclhome": str(appdata_local),
        "tomlf": str(toml_file),
        "LAUNCHED_NON_ROOT": user,
        "XDG_CONFIG_HOME": xdg
    }
    for name, value in export_a.items():
        if value:
            print(f"export {name}={shlex.quote(str(value))}")


if __name__ == "__main__":
    sys.exit(get_exports())

# Notes and drafting:
# using an app specific gpupg home cluttered the folder and proved to be more difficult than just using the users homedir
# gnupg_home = appdata_local / "gnupg"
# print(f'export GNUPGHOME={shlex.quote(str(gnupg_home))}')
