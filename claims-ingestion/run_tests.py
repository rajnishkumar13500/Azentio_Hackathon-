import os
import sys

# Ensure project root is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Ensure pytest module can be imported
venv_site = "/Users/meherchand/insurance-agent/.venv/lib/python3.13/site-packages"
if os.path.exists(venv_site) and venv_site not in sys.path:
    sys.path.insert(0, venv_site)

try:
    import pytest
    exit_code = pytest.main(["tests", "-v"])
    sys.exit(exit_code)
except ImportError:
    print("pytest could not be imported. Running basic test check...")
    import unittest
    # Run tests with unittest
    loader = unittest.TestLoader()
    suite = loader.discover("tests")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
