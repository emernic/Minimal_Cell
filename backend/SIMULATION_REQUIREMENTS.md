# Full CME-ODE Simulation Requirements

This document describes what's needed to run the full hybrid CME-ODE simulation
of the JCVI-Syn3A minimal cell, as opposed to the simplified ODE-only simulation
currently implemented.

## Current Implementation

The current `simulation.py` implements a **simplified metabolic ODE model** that:
- Uses real kinetic parameters from the model data files
- Simulates core metabolic pathways (glycolysis, TCA cycle, energy metabolism)
- Produces realistic time-series output
- Can be swapped for the full simulation when dependencies are resolved

## Full CME-ODE Hybrid Simulation

The original simulation in `/CME_ODE/program/` implements a sophisticated hybrid
model that couples:

1. **CME (Chemical Master Equation)** - Stochastic simulation of:
   - Transcription (gene → mRNA)
   - Translation (mRNA → protein)
   - mRNA degradation
   - DNA replication

2. **ODE (Ordinary Differential Equations)** - Deterministic simulation of:
   - ~800 metabolic reactions
   - Energy metabolism (ATP, GTP production/consumption)
   - Amino acid metabolism
   - Nucleotide synthesis
   - Lipid biosynthesis

The CME and ODE components are synchronized every simulated second via the
`hook.py` module.

## Dependencies Required

### Core Dependencies

```bash
# Python version
Python 3.7.x (required for pyLM compatibility)

# Scientific Python stack
numpy
scipy
pandas
biopython

# ODE model builder (included in repo)
cd /home/user/Minimal_Cell/odecell
pip install .

# SBtab for kinetic parameter files
pip install sbtab

# COBRA for metabolic modeling
pip install cobra
```

### Lattice Microbes (pyLM) - Critical Dependency

The CME solver requires **Lattice Microbes**, a high-performance stochastic
simulation package. This is the most challenging dependency.

#### Option 1: Conda Installation (Recommended)

```bash
# Create conda environment
conda create -n lm_env python=3.7
conda activate lm_env

# Clone and build Lattice Microbes
git clone https://github.com/Luthey-Schulten-Lab/Lattice_Microbes.git
cd Lattice_Microbes

# Install dependencies
conda install -c conda-forge cmake swig hdf5 h5py protobuf

# Build
mkdir build && cd build
cmake ../src/ -D MPD_GLOBAL_T_MATRIX=True -D MPD_GLOBAL_R_MATRIX=True
make && make install
```

#### Option 2: Pre-built AWS Image

Lattice Microbes provides pre-built AWS AMI images:
```bash
curl -s https://s3.amazonaws.com/lm-deploy/install | bash
```

Note: These are compiled for Python 3.5 and may not work with newer Python versions.

#### Option 3: Docker

Build a Docker image with Lattice Microbes pre-installed. See the official
documentation at https://luthey-schulten.chemistry.illinois.edu/lm/

### Optional: GPU Acceleration

For RDME (spatially-resolved) simulations:
```bash
# CUDA toolkit
# NVIDIA GPU with compute capability 6.0+
cmake ../src/ -D CUDA_ARCHITECTURES="60;70;75;80;86"
```

### Optional: High-Performance ODE Solver

For faster ODE integration:
```bash
# System dependency: SUNDIALS
apt-get install libsundials-dev  # Ubuntu/Debian
dnf install sundials-devel       # Fedora

# Python wrapper
pip install pycvodes
```

## Running the Full Simulation

Once dependencies are installed:

```bash
cd /home/user/Minimal_Cell/CME_ODE/program

# Run initial setup (minute 0)
python MinCell_CMEODE.py -procid 0 -t 1

# Run subsequent minutes
python MinCell_restart.py -procid 0 -t 125 -rs 1

# Or run with MPI for multiple replicates
mpirun -np 5 python mpi_wrapper.py -st cme-ode -t 125 -rs 1
```

## Integrating with the Backend

To use the full CME-ODE simulation with the backend API:

1. **Modify `simulation.py`** to call the CME-ODE code instead of the simplified model

2. **Update the hook function** (`hook.py` or `hook_restart.py`) to call the
   database save function after each timestep:

   ```python
   # In hook.py, after line 208:
   # in_out.writeResults(self.species, model, resFinal, time, self.procID)

   # Add:
   import database
   database.save_result(
       simulation_id=self.simulation_id,
       time_seconds=time,
       metabolites=self._extract_metabolites(self.species),
       fluxes=self._extract_fluxes(model, resFinal),
       cell_metrics=self._extract_cell_metrics(self.species)
   )
   ```

3. **Handle the subprocess architecture**: The CME-ODE simulation is designed to
   run as a subprocess that saves to files. For real-time streaming, modify it to
   write to the database instead.

## Data Files Required

All data files are present in `/home/user/Minimal_Cell/CME_ODE/model_data/`:

- `syn3A.gb`, `syn2.gb` - Genome sequences
- `proteomics.xlsx` - Protein abundances
- `Central_AA_Zane_Balanced_direction_fixed_nounqATP.tsv` - Metabolic reactions
- `Nucleotide_Kinetic_Parameters.tsv` - Nucleotide pathway kinetics
- `lipid_NoH2O_balanced_model.tsv` - Lipid metabolism
- `GlobalParameters_Zane-TB-DB.csv` - Media and cell parameters
- `mRNA_counts.csv` - Initial mRNA copy numbers

## Architecture Notes

The current backend architecture is designed to be simulation-agnostic:

- **`database.py`** - Stores simulation results in SQLite
- **`worker.py`** - Runs simulations in background threads
- **`simulation.py`** - Simulation interface (currently simplified ODE model)

To plug in the full CME-ODE simulation:

1. Create a new class in `simulation.py` that wraps the CME-ODE code
2. Implement the same interface: `run_step(current_time, dt) -> (metabolites, fluxes, cell_metrics)`
3. The worker and API will work without modification

## References

- Lattice Microbes: https://luthey-schulten.chemistry.illinois.edu/lm/
- GitHub: https://github.com/Luthey-Schulten-Lab/Lattice_Microbes
- Paper: "A Whole-Cell Computational Model Predicts Phenotype from Genotype"
  (Thornburg et al., Cell 2022)
