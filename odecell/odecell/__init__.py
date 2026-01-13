
"""

Cell-Scale ODE Environment

.. moduleauthor:: Marcelo C. R. Melo <melomcr@gmail.com>

"""

from . import modelbuilder
from . import solver

# paropt requires pycvodes which needs SUNDIALS - make it optional
try:
    from . import paropt
    __all__ = ["modelbuilder", "solver", "paropt"]
except ImportError:
    __all__ = ["modelbuilder", "solver"]

