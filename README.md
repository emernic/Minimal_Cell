# Minimal_Cell

This directory contains the simulation files for the well-stirred and spatial models of the Minimal Cell JCVI-syn3A by Thornburg et al., 2021. Also included is the directory to install the package odecell which is used in the simulations to write the ODE equations for the metabolism.

**CME_ODE**: Contains program for well-stirred model of JCVI-syn3A capable of simulating a whole cell cycle. The modified FBAm is included in model_data/FBA/

**RDME_CME_ODE**: Contains program for spatially resolved model of the first 20 minutes of the cell cycle for JCVI-syn3A

**odecell**: Package required for metabolic reactions. Writes the reaction rates into a system of ODEs that can be given to a solver

---

## Table of Contents
- [What Cell is Being Modeled](#what-cell-is-being-modeled)
- [Overall Architecture](#overall-architecture)
- [Key Flow of Control](#key-flow-of-control)
- [Major Components & Their Roles](#major-components--their-roles)
- [Biological Systems Represented](#biological-systems-represented)
- [How Parameters Are Represented](#how-parameters-are-represented)
- [Most Explanatory Code Snippets](#most-explanatory-code-snippets)
- [Scale of the Model](#scale-of-the-model)
- [Key Data Files](#key-data-files)
- [Technologies Used](#technologies-used)
- [Simulation Output](#simulation-output)

---

## What Cell is Being Modeled

**JCVI-Syn3A** - a synthetic minimal cell created at the J. Craig Venter Institute
- Derived from *Mycoplasma mycoides*
- **473 genes** (smallest known genome that can sustain life)
- ~3.8 Mbp genome
- Full cell cycle takes ~100-125 minutes
- Genome references:
  - `syn3A.gb`: NCBI GenBank file `CP016816.2`
  - `syn2.gb`: NCBI GenBank file `CP014992.1` (intermediate strain)

---

## Overall Architecture

The model uses a **hybrid CME-ODE framework**:
- **CME (Chemical Master Equation)**: Stochastic simulation for gene expression (low copy numbers like mRNA, proteins)
- **ODE (Ordinary Differential Equations)**: Deterministic simulation for metabolism (high copy numbers like metabolites)

These two methods communicate every second to exchange molecular counts, creating a seamless integration of stochastic gene expression with deterministic biochemical networks.

### Directory Structure
```
Minimal_Cell/
├── CME_ODE/                           [WELL-STIRRED MODEL]
│   ├── program/                       [24 Python simulation files]
│   ├── model_data/                    [Biological parameters, genome, proteomics]
│   └── simulations/                   [Output results]
├── RDME_gCME_ODE/                     [SPATIAL MODEL]
│   ├── program/                       [Spatial simulation code]
│   ├── model_data/                    [Same biological data]
│   └── simulations/                   [Output results]
└── odecell/                           [ODE metabolic model builder package]
    └── ENVODE/                        [Python environment]
```

---

## Key Flow of Control

The simulation operates in three phases:

### 1. Initial Setup (`MinCell_CMEODE.py` - first minute)
```
Load genome → Load proteomics → Build CME reactions → Initialize metabolites → Save state
```

- Loads genome data from GenBank files (syn2.gb, syn3A.gb)
- Loads proteomics data to determine initial protein counts
- Creates CME simulation object with all genetic information processing (GIP) reactions
- Sets up transcription, translation, degradation, and DNA replication reactions
- Initializes metabolite concentrations from .tsv model files
- Saves initial state to .lm file (HDF5 format)

### 2. Main Restart Loop (`MinCell_restart.py` - runs in 1-min intervals)
```python
for each minute (1 to T):
    Load previous state (.lm file)
    for each second (60 times):
        CME solver runs (gene expression events)
        ↓
        MyOwnSolver.hookSimulation() bridges the systems
        ↓
        ODE solver runs (metabolism for 60 seconds)
        ↓
        Update CME particle counts
    Save results (.lm, .csv, fluxes)
```

### 3. The Critical Bridge (`hook.py` - `MyOwnSolver` class)

The **`MyOwnSolver`** class extends Lattice Microbes' GillespieDSolver and implements the hybrid integration:

```python
def hookSimulation(self, time):
    # Called every 1 second during simulation

    # 1. Get current stochastic molecule counts from CME
    self.species.update(self)

    # 2. Build deterministic ODE model with current enzyme levels
    model = Simp.initModel(self.species, ...)

    # 3. Run ODE integration for 60 seconds
    res = integrate.runODE(model, ...)

    # 4. Write metabolic fluxes and update CME particle counts
    in_out.writeResults(...)

    return 1  # Tell Lattice Microbes to accept the changes
```

### Parallel Execution
- **`mpi_wrapper.py`** enables MPI parallelization for running multiple cell replicates
- Each process gets a unique rank (process ID) for independent random number seeding

---

## Major Components & Their Roles

| Component | Purpose | Lines of Code |
|-----------|---------|---------------|
| `MinCell_CMEODE.py` | Initial simulation setup, CME network builder | ~800 |
| `MinCell_restart.py` | Restart loop controller | ~400 |
| `hook.py` / `hook_restart.py` | **THE HEART**: Bridges CME ↔ ODE | ~250 |
| `Simp.py` | Builds ODE metabolic model from current state | ~600 |
| `integrate.py` | ODE solver (uses CVODES or SciPy) | ~300 |
| `defMetRxns.py` | Defines ~800+ metabolic reactions | **~3000** |
| `Rxns.py` | Metabolic rate equations (Michaelis-Menten kinetics) | ~500 |
| `rep_start.py` / `rep_restart.py` | DNA replication & DnaA filament dynamics | ~200 |
| `species_counts.py` | CME-ODE species mapping and conversion | ~400 |
| `in_out.py` | I/O handling and cell growth calculations | ~200 |
| `setICs.py` / `setICs_two.py` | Load metabolite initial conditions | ~300 |
| `translation_rate_start.py` | Calculate translation rate constants | ~200 |
| `PPP_patch.py` | Update Pentose Phosphate Pathway | ~100 |
| `lipid_patch.py` | Update lipid metabolism parameters | ~100 |
| `mpi_wrapper.py` | MPI job launcher for parallel execution | ~100 |

### Key Module Interactions

1. **CME-ODE Communication**: `MyOwnSolver.hookSimulation()` → `species_counts.update()` → `Simp.initModel()` → `integrate.runODE()`

2. **Reaction Definition Chain**: `Rxns.py` and `defMetRxns.py` define rate equations → `Simp.py` builds the ODE model → `integrate.py` compiles with Cython or uses SciPy

3. **Data Flow**: `CME particle counts` ↔ `species_counts.SpeciesCounts` ↔ `mM concentrations` ↔ `ODE solver`

---

## Biological Systems Represented

### 1. Gene Expression (Stochastic CME)

**Transcription** - All 473 genes with individual promoter strengths
```python
# From MinCell_CMEODE.py (lines 264-307)
def TranscriptRate(rnaMetID, ptnMetID, rnasequence, jcvi2ID):
    k_transcription = kcat_mod / ((1+rnaPolK0/RnaPconc)*(rnaPolKd**2)/(CMono1*CMono2) + NMonoSum + n_tot - 1)
```
- Kcat modulated by RNA polymerase availability (from proteomics data)
- Kinetic parameters based on first 2 nucleotides and total sequence length
- Separate calculations for protein-coding, rRNA, and tRNA genes

**Translation** - Ribosome binding model with Michaelis-Menten kinetics
- All 20 canonical amino acids + formyl-methionine
- tRNA charging reactions for all 20 amino acids
- Membrane protein translocation via SecY pathway
- Codon usage based on actual gene sequences

**Degradation**
- mRNA degradation: sequence-length dependent rates (~2 minute half-life)
- Protein degradation: exponential decay (~25 hour half-life)

### 2. Central Metabolism (Deterministic ODE)

~500+ metabolic reactions including:
- **Glycolysis** (10 reactions)
- **Pentose Phosphate Pathway** (15+ reactions)
- **Citric Acid Cycle** (8 reactions)
- **Nucleotide biosynthesis** (ATP, GTP, CTP, UTP, dNTPs)
- **Amino acid metabolism** (primarily alanine synthesis)

### 3. Lipid Metabolism

- Fatty acid synthesis
- Phospholipid biosynthesis (cardiolipin, phosphatidylcholine, etc.)
- Cell membrane growth coupled to lipid biosynthesis
- Drives **cell growth** through membrane surface area accumulation

### 4. DNA Replication

From `rep_start.py` (lines 15-72):
- **DnaA-dependent initiation** with cooperative binding
- High-affinity binding sites for DnaA oligomerization
- Low-affinity ssDNA unwinding sites (30 sites simulated)
- DnaA-ATP dependent initiation
- Multi-fork replication (up to 3 simultaneous replication forks)
- Multiple replication initiation events per cell cycle

### 5. Transport Reactions

- Glucose uptake (PTS system)
- Amino acid transporters
- Ion homeostasis (K+, Mg2+, Ca2+)
- Spermine transport

---

## How Parameters Are Represented

### Global Parameters (`GlobalParameters_Zane-TB-DB.csv`)
```
External metabolite concentrations:
  - Glucose: 40 mM
  - Amino acids: 0.1 mM each
Cell radius: 200 nm (default, grows dynamically)
Ion transporter concentrations (K+, Mg2+, Ca2+, Spermine)
```

### Gene Expression Parameters (in `MinCell_CMEODE.py`)
```python
rnaPolKcat = 0.155*187/493*20  # RNA polymerase: ~1.2 nt/s
rnaPolK0 = 1e-4                # mM (binding affinity)
rnaPolKd = 0.1                 # mM (Michaelis constant)
riboKcat = 10                  # Ribosome: 10 aa/s
ptnDegRate = 7.70e-06          # Protein half-life: ~25 hours
rnaDegRate = 0.00578/2         # mRNA half-life: ~2 minutes
```

### Metabolic Parameters (.tsv model files)

- **`Central_AA_Zane_Balanced_direction_fixed_nounqATP.tsv`** (490 KB)
  - ~500+ central carbon metabolism reactions with kinetic parameters
  - Forward/reverse kcats for each enzyme
  - Michaelis constants (Km) for all substrates/products

- **`Nucleotide_Kinetic_Parameters.tsv`** (488 KB)
  - NTP/dNTP synthesis pathway parameters

- **`lipid_NoH2O_balanced_model.tsv`** (39 KB)
  - Lipid biosynthesis reactions for cell growth

### Initial Conditions (from .csv and .xlsx files)

```
protein_metabolites_frac.csv        [16 entries] - Selected proteins & fractions
membrane_protein_metabolites.csv    [~40 entries] - Membrane proteins
ribo_protein_metabolites.csv        [~10 entries] - Ribosomal proteins
trna_metabolites_synthase.csv       [20 entries] - tRNA synthases
rrna_metabolites_1.csv & 2.csv      [rRNA genes] - Ribosomal RNA
mRNA_counts.csv                     [480+ genes] - mRNA steady-state counts
```

### Proteomics Data (`proteomics.xlsx`)
- ~480+ proteins with quantified abundance (from mass spectrometry)
- Used to set initial protein counts and transcription rate modulation
- Maps MMSYN1, JCVISYN3A, and AOE protein identifiers

---

## Most Explanatory Code Snippets

### 1. Cell Growth Calculation
From `in_out.py:34-80`:
```python
# Cell surface area = lipid headgroups + membrane protein area
SA_lipid = sum(lipid_concentrations * headgroup_areas)
SA_protein = num_membrane_proteins * 28  # nm² per protein
total_SA = SA_lipid + SA_protein
# Volume scales with surface area accumulation
```

### 2. The Hybrid Integration Hook
From `hook.py:107-237` - **THE CRITICAL BRIDGE**:
```python
def hookSimulation(self, time):
    # Called every 1 second during simulation

    # 1. Get current stochastic molecule counts from CME
    self.species.update(self)

    # 2. Build deterministic ODE model with current enzyme levels
    model = Simp.initModel(self.species, ...)

    # 3. Run ODE integration for 60 seconds
    res = integrate.runODE(model, ...)

    # 4. Write metabolic fluxes and update CME particle counts
    in_out.writeResults(...)

    return 1  # Tell Lattice Microbes to accept the changes
```

### 3. Translation Rate with Amino Acid Availability
From `translation_rate_start.py`:
```python
def TranslatRate(rnaMetID, ptnMetID, rnasequence, aasequence):
    # Counts each amino acid in protein sequence
    # Calculates rate based on charged tRNA availability
    # Uses Michaelis-Menten kinetics for all 20 amino acids
    # Returns k_translation for this specific protein
```

### 4. DNA Replication Initiation
From `rep_start.py`:
```python
# DnaA oligomerization on high-affinity sites
# ssDNA unwinding at 30 low-affinity sites
# DnaA-ATP dependent with cooperativity
# Enables multiple replication initiation events
```

---

## Scale of the Model

- **~800+ molecular species**:
  - ~480 proteins
  - ~480 mRNAs
  - ~50+ metabolites
  - ~20 tRNAs (charged/uncharged pairs)
  - Ribosomal RNAs
  - Nucleotide pools and cofactors

- **~1,300+ reactions**:
  - ~500+ metabolic ODE reactions
  - ~800+ CME reactions (transcription, translation, degradation, replication)

- **Simulation time**: Full cell cycle (100-125 minutes by default)

---

## Key Data Files

| File | Size | Purpose |
|------|------|---------|
| `syn3A.gb` | 1.2 MB | Complete Syn3A genome in GenBank format |
| `Central_AA_Zane_Balanced_direction_fixed_nounqATP.tsv` | 490 KB | Central metabolic reactions (~500) with kinetic parameters |
| `Nucleotide_Kinetic_Parameters.tsv` | 488 KB | NTP/dNTP synthesis pathway parameters |
| `proteomics.xlsx` | 160 KB | Quantitative proteomics data for ~480 proteins |
| `mRNA_counts.csv` | 18 KB | Steady-state mRNA copy numbers |
| `GlobalParameters_Zane-TB-DB.csv` | 2.6 KB | Media composition, cell radius, ion concentrations |
| `lipid_NoH2O_balanced_model.tsv` | 39 KB | Lipid biosynthesis pathways |
| `transport_NoH2O_Zane-TB-DB.tsv` | 12 KB | Nutrient transport reactions |

---

## Simulation Output

Upon running a simulation, outputs include:

1. **`.lm` file** (HDF5 format): Complete time-series of all species particle counts
2. **`.csv` file**: Comma-separated species counts at each timestep
3. **`.log` file**: Simulation debug information
4. **`fluxes/*.csv` files**: Metabolic reaction flux data at each minute
5. **Growth metrics**: Cell volume and surface area progression

---

## Technologies Used

- **pyLM (Lattice Microbes)**: CME solver with GPU support for stochastic chemical kinetics
- **odecell**: Custom ODE model builder for metabolic networks
- **SciPy/CVODES**: ODE integration for deterministic biochemical reactions
- **Cython**: JIT compilation for ODE solver performance optimization
- **BioPython**: Genome parsing and sequence operations
- **Pandas**: Data manipulation and analysis
- **MPI4Py**: Parallel execution for multiple cell replicates

---

## Spatial Model (RDME_gCME_ODE)

The spatial variant in `RDME_gCME_ODE/`:
- Uses **Reaction-Diffusion Master Equation (RDME)** for spatial resolution
- Simulates only first **20 minutes** of cell cycle
- Divides cell into voxels with diffusion between compartments
- Requires **GPU acceleration** (CUDA 10+, tested on NVIDIA Titan V, Tesla V100)
- Uses same biological parameters but enables spatial heterogeneity

---

## Summary

This represents one of the most comprehensive whole-cell computational models currently available, integrating stochastic gene expression (CME) with deterministic metabolism (ODE) in a hybrid framework to simulate a complete minimal cell cycle. The model captures essentially every major biological process in a living cell - from DNA replication through transcription and translation to metabolism and cell growth - making it a powerful tool for understanding cellular systems biology.
