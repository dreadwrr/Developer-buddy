import tomllib
import shlex

with open("/usr/local/save-changesnew/config.toml", "rb") as f:
    config = tomllib.load(f)

# List of sections you want to flatten directly
flatten_sections = ['backend', 'logs', 'search', 'analytics', 'display', 'diagnostics', 'paths']

for section in flatten_sections:
    section_data = config.get(section, {})
    for k, v in section_data.items():
        # Handle booleans as "true"/"false"
        val = str(v).lower() if isinstance(v, bool) else str(v)
        print(f'export {k}={shlex.quote(val)}')
