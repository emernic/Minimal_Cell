# Minimal_Cell

Hybrid CME-ODE whole-cell model of JCVI-syn3A (473 genes, ~3.8 Mbp genome). Simulates gene expression stochastically (CME) and metabolism deterministically (ODE), coupled every second.

**CME_ODE**: Well-stirred model, full cell cycle (~100-125 min)
**RDME_CME_ODE**: Spatial model, first 20 min only, requires GPU
**odecell**: Package for building ODE metabolic models

## Table of Contents
- [Model Organism](#model-organism)
- [Architecture](#architecture)
- [Execution Flow](#execution-flow)
- [File Roles](#file-roles)
- [Biological Systems](#biological-systems)
- [Parameters](#parameters)
- [Key Code Patterns](#key-code-patterns)
- [Data Files](#data-files)
- [Output](#output)

---

## Model Organism

**JCVI-Syn3A**: Synthetic minimal *Mycoplasma mycoides*
- 473 genes, ~3.8 Mbp genome
- Cell cycle: 100-125 minutes
- GenBank: `syn3A.gb` (CP016816.2), `syn2.gb` (CP014992.1)

## Architecture

**Hybrid CME-ODE**:
- CME: Stochastic gene expression (mRNA, proteins) via Gillespie algorithm
- ODE: Deterministic metabolism (metabolites) via CVODES/SciPy
- Communication: Every 1 second, CME particle counts → ODE concentrations → CME updates

**Directory Structure**:
```
CME_ODE/program/         # 24 Python files
CME_ODE/model_data/      # Genome, proteomics, kinetic parameters
CME_ODE/simulations/     # Output (.lm, .csv, fluxes)
odecell/                 # ODE model builder
```

## Execution Flow

**1. Initial Setup** (`MinCell_CMEODE.py`, minute 0):
- Load genome (`syn3A.gb`, `syn2.gb`)
- Load proteomics (`proteomics.xlsx`) → initial protein counts
- Build CME reactions (transcription, translation, degradation, replication)
- Initialize metabolites from `.tsv` files
- Save to `.lm` file (HDF5)

**2. Main Loop** (`MinCell_restart.py`, minutes 1→T):
```python
for minute in range(1, T):
    load .lm file
    for second in range(60):
        CME solver (Gillespie)
        MyOwnSolver.hookSimulation()  # CME ↔ ODE bridge
        ODE solver (60 sec integration)
        update CME counts
    save .lm, .csv, fluxes
```

**3. CME-ODE Bridge** (`hook.py`):
```python
# MyOwnSolver.hookSimulation() - called every 1 second
def hookSimulation(self, time):
    self.species.update(self)             # CME → particle counts
    model = Simp.initModel(self.species)  # Build ODE system
    res = integrate.runODE(model, 60)     # Integrate 60 sec
    in_out.writeResults(res)              # ODE → CME counts
    return 1
```

**Parallelization**: `mpi_wrapper.py` runs multiple replicates via MPI

## File Roles

| File | Purpose |
|------|---------|
| `MinCell_CMEODE.py` | Initial simulation setup, builds CME reaction network |
| `MinCell_restart.py` | Restart loop controller (minutes 1→T) |
| `hook.py` / `hook_restart.py` | CME ↔ ODE bridge (`MyOwnSolver.hookSimulation()`) |
| `Simp.py` | Builds ODE model from current CME state |
| `integrate.py` | ODE integrator (CVODES/SciPy wrapper) |
| `defMetRxns.py` | Defines ~800 metabolic reactions (~3000 lines) |
| `Rxns.py` | Metabolic rate law functions (Michaelis-Menten) |
| `rep_start.py` / `rep_restart.py` | DNA replication, DnaA filament dynamics |
| `species_counts.py` | Maps species between CME (counts) ↔ ODE (mM) |
| `in_out.py` | I/O, cell growth calculation (lipid + protein → surface area) |
| `setICs.py` / `setICs_two.py` | Load metabolite initial conditions |
| `translation_rate_start.py` | Calculate translation rates (tRNA-dependent) |
| `PPP_patch.py` | Pentose Phosphate Pathway parameter updates |
| `lipid_patch.py` | Lipid metabolism parameter updates |
| `mpi_wrapper.py` | MPI parallelization wrapper |

**Call chain**: `hookSimulation()` → `species_counts.update()` → `Simp.initModel()` → `integrate.runODE()` → `in_out.writeResults()`

## Biological Systems

**Gene Expression** (CME):
- Transcription: 473 genes, rate depends on RNA pol availability, promoter strength
- Translation: Michaelis-Menten, 20 amino acids + fMet, tRNA charging, SecY translocation
- Degradation: mRNA t₁/₂ ~2 min, protein t₁/₂ ~25 hr

**Metabolism** (ODE, ~500 reactions):
- Glycolysis, Pentose Phosphate Pathway, TCA cycle
- Nucleotide biosynthesis (NTPs, dNTPs)
- Amino acid metabolism (mainly alanine)
- Lipid biosynthesis (fatty acids, phospholipids)

**DNA Replication** (CME):
- DnaA-dependent initiation, cooperative binding
- High-affinity (oligomerization) and low-affinity (ssDNA unwinding, 30 sites)
- Multi-fork replication (up to 3 forks)

**Transport**: Glucose (PTS), amino acids, ions (K⁺, Mg²⁺, Ca²⁺, spermine)

**Cell Growth**: Surface area = lipid headgroups + membrane proteins (28 nm²/protein), volume scales with SA

## Parameters

**Global** (`GlobalParameters_Zane-TB-DB.csv`):
- Glucose: 40 mM, amino acids: 0.1 mM each
- Cell radius: 200 nm (grows dynamically)
- Ion concentrations (K⁺, Mg²⁺, Ca²⁺, spermine)

**Gene Expression** (`MinCell_CMEODE.py`):
```python
rnaPolKcat = 0.155*187/493*20  # ~1.2 nt/s
riboKcat = 10                  # 10 aa/s
ptnDegRate = 7.70e-06          # protein t₁/₂ ~25 hr
rnaDegRate = 0.00578/2         # mRNA t₁/₂ ~2 min
```

**Metabolic** (`.tsv` files):
- `Central_AA_Zane_Balanced_direction_fixed_nounqATP.tsv`: ~500 reactions, kcats, Kms
- `Nucleotide_Kinetic_Parameters.tsv`: NTP/dNTP pathways
- `lipid_NoH2O_balanced_model.tsv`: Lipid biosynthesis

**Initial Conditions** (`.csv`, `.xlsx`):
- `proteomics.xlsx`: ~480 proteins, mass spec abundances
- `mRNA_counts.csv`: Steady-state mRNA copies
- `protein_metabolites_frac.csv`, `membrane_protein_metabolites.csv`, `ribo_protein_metabolites.csv`, `trna_metabolites_synthase.csv`, `rrna_metabolites_*.csv`

## Key Code Patterns

**Transcription rate** (`MinCell_CMEODE.py:264-307`):
```python
k_transcription = kcat_mod / ((1+rnaPolK0/RnaPconc)*(rnaPolKd**2)/(CMono1*CMono2) + NMonoSum + n_tot - 1)
```
Modulated by RNA pol availability, depends on first 2 nucleotides + sequence length.

**Translation rate** (`translation_rate_start.py`):
```python
# Michaelis-Menten based on charged tRNA availability for all 20 amino acids
# Counts each AA in protein sequence, calculates k_translation
```

**Cell growth** (`in_out.py:34-80`):
```python
SA = sum(lipid_conc * headgroup_area) + n_membrane_proteins * 28  # nm²
# Volume scales with SA
```

**DNA replication** (`rep_start.py:15-72`):
- DnaA oligomerization (high-affinity sites)
- ssDNA unwinding (30 low-affinity sites)
- DnaA-ATP dependent, cooperative

## Data Files

| File | Purpose |
|------|---------|
| `syn3A.gb` | Syn3A genome (GenBank) |
| `Central_AA_Zane_Balanced_direction_fixed_nounqATP.tsv` | ~500 metabolic reactions, kcats, Kms |
| `Nucleotide_Kinetic_Parameters.tsv` | NTP/dNTP pathway kinetics |
| `proteomics.xlsx` | ~480 proteins, experimental abundances |
| `mRNA_counts.csv` | Steady-state mRNA counts |
| `GlobalParameters_Zane-TB-DB.csv` | Media, cell radius, ion conc |
| `lipid_NoH2O_balanced_model.tsv` | Lipid biosynthesis |
| `transport_NoH2O_Zane-TB-DB.tsv` | Nutrient transport |

## Output

- `.lm` (HDF5): Time-series of all species counts
- `.csv`: Species counts at each timestep
- `.log`: Debug info
- `fluxes/*.csv`: Metabolic fluxes per minute
- Growth metrics: Cell volume, surface area

## Dependencies

- pyLM (Lattice Microbes): CME solver
- odecell: ODE model builder
- SciPy/CVODES: ODE integration
- Cython: JIT compilation
- BioPython, Pandas, MPI4Py
