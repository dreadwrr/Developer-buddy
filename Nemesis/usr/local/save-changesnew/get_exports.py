import tomllib
import shlex

with open("/usr/local/save-changesnew/config.toml", "rb") as f:
    config = tomllib.load(f)

# List of sections you want to flatten directly (including the ones in 'paths' and 'search')
nested_sections = {
    'mMODE': ['search'],
    'analytics': ['STATPST'],
    'backend': ['backend'],
    'pydbpst': ['paths'] 
    'logpst': ['paths'],
    'statpst': ['paths']
}

for section, parent_sections in nested_sections.items():
    for parent_section in parent_sections:
        section_data = config.get(parent_section, {}).get(section, {})
        for k, v in section_data.items():
            # Handle booleans as "true"/"false"
            val = str(v).lower() if isinstance(v, bool) else str(v)
            print(f'export {k}={shlex.quote(val)}')

# all
# List of sections you want to flatten directly
#flatten_sections = ['backend', 'logs', 'search', 'analytics', 'display', 'diagnostics', 'paths']
#
#for section in flatten_sections:
#    section_data = config.get(section, {})
#    for k, v in section_data.items():
#        # Handle booleans as "true"/"false"
#        val = str(v).lower() if isinstance(v, bool) else str(v)
#        print(f'export {k}={shlex.quote(val)}')
