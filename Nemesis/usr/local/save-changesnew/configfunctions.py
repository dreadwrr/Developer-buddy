import getpass
import os
import pwd
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


# app location
def find_install():
    # wdir = Path(sys.argv[0]).resolve().parent  # calling script
    # wdir = Path(__file__).resolve().parent.parent  # if files are moved to a src or seperate directory its the one below it
    wdir = Path(__file__).resolve().parent
    return wdir


def not_absolute(user_path: str, quiet=False) -> bool:
    p = Path(user_path)
    if p.is_absolute():
        if not quiet:
            print("proteus_EXTN path cant be absolute: ", p)
        # raise ValueError("Absolute paths not allowed")
        return False
    return True


def get_user():
    """ read from environ inaccurate """
    user = None
    try:
        user = getpass.getuser()
        #  user = pwd.getpwuid(os.geteuid()).pw_name
    except (KeyError, OSError):
        print("unable to get username attempting fallback")
    if not user:
        try:
            user = Path.home().parts[-1]
        except RuntimeError as e:
            raise RuntimeError("unable to find current user.") from e
    return user


def user_info(user=None):
    try:
        if user:
            usr_info = pwd.getpwnam(user)
        else:
            usr_info = pwd.getpwuid(os.geteuid())
        USR = usr_info.pw_name
        uid = usr_info.pw_uid
        gid = usr_info.pw_gid  # gid = grp.getgrnam(user).gr_gid
        home_dir = Path(usr_info.pw_dir)

        return USR, uid, gid, home_dir
    except (KeyError, OSError):
        raise ValueError(f"unable to get user info for {user if user else 'current user'}")


# def ensure_default_utils():
#     required = ["md5sum", "find"]
#     missing = [cmd for cmd in required if shutil.which(cmd) is None]
#     if missing:
#         missing_str = ", ".join(missing)
#         raise RuntimeError(f"Missing required utility(s): {missing_str}")

#     try:
#         out = subprocess.run(
#             ["find", "--version"],
#             capture_output=True,
#             text=True,
#             check=True
#         ).stdout
#     except Exception as e:
#         raise RuntimeError(f"Unable to validate GNU find: {type(e).__name__} {e}")

#     if "GNU findutils" not in out:
#         raise RuntimeError("Unsupported `find` detected. GNU findutils is required.")


# toml


def get_config(appdata_local=None, user=None):
    """ user configuration location """
    home_dir = None
    config_file = "config (copy).toml"

    if appdata_local:
        default_conf = appdata_local / "config" / config_file
    else:
        default_conf = Path(os.path.join("/usr/local/save-changesnew/config", config_file))

    user, uid, gid, home_dir = user_info(user)

    xdg_config = os.environ.get("XDG_CONFIG_HOME")

    # if xdg_config:
    #     config_home = Path(xdg_config)

    # elif home_dir:
    #     config_home = home_dir / ".config"
    # else:
    #     if user == "root":
    #         default_conf_home = "/root/.config"
    #     else:
    #         default_conf_home = f"/home/{user}/.config"
    #     config_home = Path(default_conf_home)

    # config_local = config_home / "save-changesnew"
    # os.makedirs(config_local, mode=0o755, exist_ok=True)
    config_local = appdata_local / "config"
    toml_file = config_local / "config.toml"

    toml_missing = not toml_file.is_file()
    # first_time_setup = toml_missing

    if toml_missing and default_conf.is_file():
        shutil.copy(default_conf, toml_file)
    elif toml_missing:
        raise ValueError(f"No default configuration found at {default_conf}.")

    # if first_time_setup:
    #     ensure_default_utils()

    if toml_file.is_file():
        return toml_file, home_dir, xdg_config, uid, gid
    raise FileNotFoundError(f"Unable to find config.toml config file in {config_local}")


def load_toml(conf_path):  # tomllib standard library. does not preserve commenting**
    if not conf_path.is_file():
        print("Unable to find config file:", conf_path)
        sys.exit(1)
    try:
        with open(conf_path, 'rb') as f:
            config = tomllib.load(f)
    except Exception as e:
        print(f"Failed to parse TOML: {e}")
        sys.exit(1)

    return config


# update the toml to disable\enable
def update_toml_setting(keyName, settingName, newValue, filePath):

    def format_toml_value(value):
        if isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, str):
            return f'"{value}"'
        elif value is None:
            return '""'
        elif isinstance(value, list):
            # Format as TOML array
            items = []
            for item in value:
                if isinstance(item, str):
                    items.append(f'"{item}"')
                elif isinstance(item, bool):
                    items.append(str(item).lower())
                else:
                    items.append(str(item))
            return "[" + ", ".join(items) + "]"
        else:
            return str(value)

    try:

        fnd = False

        with open(filePath, "r") as f:
            lines = f.readlines()

        with open(filePath, "w") as f:
            for line in lines:
                stripped = line.strip()
                if not fnd and stripped.startswith(f"{settingName}"):
                    fnd = True

                    value_str = format_toml_value(newValue)

                    if "#" in line:
                        _, comment = line.split("#", 1)
                        comment = " #" + comment.rstrip("\n")
                    else:
                        comment = ""

                    f.write(f"{settingName} = {value_str}{comment}\n")
                else:
                    f.write(line)

    except Exception as e:
        print(f"Failed to update toml {filePath} setting. check key value pair {type(e).__name__} {e}")
        raise


def update_config(config_file, setting_name, old_value, quiet=False, lclhome=None):
    """ use sed to update a file """
    script_file = "updateconfig.sh"
    script_path = "/usr/local/save-changesnew/" + script_file
    if lclhome:
        script_path = os.path.join(lclhome, script_file)
    cmd = [
        script_path,
        str(config_file),
        setting_name,
        old_value
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        if not quiet:
            print(result)
    else:
        print(result)
        print(f'Bash script failed {script_path}. error code: {result.returncode}')

# end Toml
