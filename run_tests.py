
import pytest
import sys

# Add current directory to path
sys.path.append('.')

class Tee(object):
    def __init__(self, name, mode):
        self.file = open(name, mode)
        self.stdout = sys.stdout
        sys.stdout = self
    def __del__(self):
        sys.stdout = self.stdout
        self.file.close()
    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)
    def flush(self):
        self.file.flush()
        self.stdout.flush()
    def isatty(self):
        return False

# Redirect stdout to file
sys.stdout = Tee('test_output.log', 'w')
sys.stderr = sys.stdout

print("Running tests...")
try:
    retcode = pytest.main(["-v", "tests/test_event_errors.py"])
    print(f"Tests finished with code: {retcode}")
except Exception as e:
    print(f"Error running tests: {e}")
    retcode = 1

sys.exit(retcode)
