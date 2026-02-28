#!/usr/bin/env python3
import tomllib
import shlex
import sys
from configfunctions import find_install
from configfunctions import get_config
from logs import check_log_perms


def get_exports():
    if len(sys.argv) < 2:
        print("Usage: get_exports.py <username>", file=sys.stderr)
        sys.exit(1)
    user = sys.argv[1]

    appdata_local = find_install()  # software install aka workdir
    log_dir = appdata_local / "logs"

    toml_file, _, xdg_config, _, _ = get_config(appdata_local, user)
    with open(toml_file, "rb") as f:
        config = tomllib.load(f)

    if user != "root":
        user_log = config.get("logs", {}).get("userLOG")
        log_path = log_dir / user_log
        check_log_perms(log_path)
        # ll_level = config['search']['logLEVEL']
        # setup_logger(log_path, ll_level, "EXPORTS")

    # to /usr/local/bin/recentchanges
    nested_sections = {
        'email': ['backend'],
        'name': ['backend'],
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

    export_a = {
        "lclhome": str(appdata_local),
        "tomlf": str(toml_file),
        "LAUNCHED_NON_ROOT": user,
        "XDG_CONFIG_HOME": xdg_config
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
