import uvicorn
import sys
import os
from openenv_core.env_server import create_app

# Ensure we can find environment.py in the root folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from environment import EVFleetAdapter, EVAction, EVObservation

# Create the app instance (Passing the CLASS, not an instance)
app = create_app(EVFleetAdapter, EVAction, EVObservation, env_name="ev-fleet-charging")

def main():
    """Explicit main function required by the validator."""
    print("Launching EV Fleet Charging Server...")
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()