# PMBM Six-Pulse Inverter Analysis - Summary

## Problem Statement

Analyze a three-phase, 8-pole, 6000-rpm Permanent Magnet Brushless Motor (PMBM) fed from a six-pulse inverter with two-phase conduction. Calculate:
1. Shaft torque
2. Electromagnetic torque
3. Losses in the stator winding

## Quick Answer

| **Result** | **Value** |
|------------|-----------|
| **Electromagnetic Torque (Te)** | **154.93 Nm** |
| **Shaft Torque (Tshaft)** | **154.93 Nm** |
| **Copper Losses (Pcu)** | **31.36 kW** |

## Key Formulas Used

### 1. Back EMF
```
EMF_LL = kE × speed = 0.072 × 6000 = 432 V
```

### 2. Current
```
I = (Vdc - EMF_LL) / R1L = (600 - 432) / 0.9 = 186.67 A
```

### 3. Electromagnetic Torque
```
Te = kT × I = 0.83 × 186.67 = 154.93 Nm
```

### 4. Copper Losses
```
Pcu = I² × R1L = (186.67)² × 0.9 = 31.36 kW
```

## Files Created

1. **pmbm_inverter_simulation.py** - Main interactive visualization with sliders
2. **test_pmbm_calculations.py** - Calculation verification script
3. **PMBM_INVERTER_README.md** - Detailed documentation
4. **PMBM_SUMMARY.md** - This summary file

## Running the Code

### Quick Calculations Only
```bash
python test_pmbm_calculations.py
```

### Full Interactive Visualization
```bash
python pmbm_inverter_simulation.py
```

## Features

### Interactive Sliders
- **Vdc**: DC bus voltage (100-1000 V)
- **R1L**: Line-to-line resistance (0.1-5.0 Ω)
- **L1L**: Line-to-line inductance (1.0-20.0 mH)
- **kE**: EMF constant (0.01-0.2 V/rpm)
- **kT**: Torque constant (0.1-2.0 Nm/A)
- **Speed**: Motor speed (1000-10000 rpm)

### 8 Real-Time Visualizations
1. **Circuit Diagram** - Inverter topology and motor connection
2. **Voltage Waveforms** - Line-to-line voltage and back EMF
3. **Current Waveform** - Phase current over time
4. **Power Flow** - Power distribution through the system
5. **Torque Analysis** - Electromagnetic vs shaft torque
6. **Torque-Speed Curve** - Characteristic curve
7. **Efficiency Curve** - Efficiency vs speed
8. **Loss Breakdown** - Pie chart of losses

## Technical Details

### Six-Pulse Inverter Operation
- Two phases conduct at any instant
- Six distinct states per electrical cycle
- Each state lasts 60° electrical
- Line-to-line voltage = Vdc during conduction

### Power Balance
```
Input Power (Pin)     = 112.00 kW
- Copper Losses (Pcu) =  31.36 kW
= Output Power (Pem)  =  80.64 kW
Efficiency (η)        =  72.00 %
```

## Educational Value

This simulation demonstrates:
- Motor-inverter interaction
- Effect of parameters on performance
- Power loss mechanisms
- Torque production in PMBM
- Efficiency optimization

## Applications

Relevant for:
- Electric vehicle drives
- Industrial servo systems
- Robotics actuators
- HVAC compressors
- Aerospace applications

---

**Repository**: advnaced-sieci9
**Created**: 2025-11-20
**Purpose**: Advanced electrical networks analysis
