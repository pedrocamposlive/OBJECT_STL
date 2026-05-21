from engines.triposr_engine import TripoSREngine
from engines.instantmesh_engine import InstantMeshEngine
from engines.depth_engine import DepthEngine

ENGINES = {
    "1": TripoSREngine,
    "2": InstantMeshEngine,
    "3": DepthEngine,
}
