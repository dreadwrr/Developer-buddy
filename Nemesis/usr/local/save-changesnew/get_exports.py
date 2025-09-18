# get_config_exports.py
import tomllib

with open("/usr/local/save-changesnew/config.toml", "rb") as f:
    config = tomllib.load(f)

for k, v in config.items():
    if isinstance(v, bool):
        v = "true" if v else "false"
    print(f'export {k.upper()}="{v}"')