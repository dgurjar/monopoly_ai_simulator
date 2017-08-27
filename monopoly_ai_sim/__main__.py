import sys
import os.path

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(base_path)

from monopoly_ai_sim.simulator import Simulator
if __name__ == '__main__':
    Simulator().run()
