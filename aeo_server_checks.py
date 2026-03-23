"""AEO check functions — extracted for testability.

Loads aeo-server.py via importlib (hyphenated filename) and re-exports
check functions. The module reference `_mod` is exposed so tests can
patch `_mod.requests.get` and `_mod.time.time` at the right namespace.
"""

import importlib.util
import os
import sys

# Load aeo-server.py as a module
_server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aeo-server.py")
_spec = importlib.util.spec_from_file_location("aeo_server", _server_path)
_mod = importlib.util.module_from_spec(_spec)

# Prevent HTTPServer from starting — guard the if __name__ block
# We need to set __name__ to something other than __main__
_mod.__name__ = "aeo_server"

# Minimal argv so PORT defaults work
_original_argv = sys.argv[:]
sys.argv = ["test"]

try:
    _spec.loader.exec_module(_mod)
except SystemExit:
    pass  # In case server code calls sys.exit
finally:
    sys.argv = _original_argv

# Re-export check functions (these reference _mod.requests / _mod.time internally)
check_structured_data = _mod.check_structured_data
check_robots_txt = _mod.check_robots_txt
check_llms_txt = _mod.check_llms_txt
check_content_structure = _mod.check_content_structure
check_tool_api = _mod.check_tool_api
check_performance = _mod.check_performance
check_markdown_agents = _mod.check_markdown_agents

# Expose module ref for targeted patching
server_module = _mod
MODULE_NAME = "aeo_server"  # the name under which _mod was loaded
