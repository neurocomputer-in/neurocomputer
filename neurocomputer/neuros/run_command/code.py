import subprocess

async def run(state, *, command):
    def _lazy_import(name, pip_name=None):
        try:
            return __import__(name)
        except ImportError:
            import subprocess, sys, importlib
            subprocess.check_call([
                sys.executable, '-m', 'pip', pip_name or name
            ])
            return importlib.import_module(name)

    # Execute the command
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return {'output': result.stdout if result.returncode == 0 else result.stderr}