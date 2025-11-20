# PMBM Six-Pulse Inverter Simulation

## Overview
This simulation analyzes a three-phase, 8-pole, 6000-rpm Permanent Magnet Brushless Motor (PMBM) fed from a six-pulse inverter with two-phase conduction mode.

## System Parameters

### Given Parameters:
- **DC Bus Voltage (Vdc)**: 600 V
- **Line-to-Line Resistance (R1L)**: 0.9 Ω
- **Line-to-Line Inductance (L1L)**: 5.0 mH
- **EMF Constant (kE)**: 0.072 V/rpm
- **Torque Constant (kT)**: 0.83 Nm/A
- **Motor Speed**: 6000 rpm
- **Number of Poles**: 8

## Mathematical Analysis

### 1. Back EMF Calculation
For a PMBM, the back EMF (line-to-line) is:
```
EMF_LL = kE × speed
EMF_LL = 0.072 × 6000 = 432 V
```

### 2. Current Calculation
In a six-pulse inverter with two phases on, the applied voltage equals the DC bus voltage:
```
I = (Vdc - EMF_LL) / R1L
I = (600 - 432) / 0.9 = 186.67 A
```

### 3. Electromagnetic Torque
The electromagnetic torque is:
```
Te = kT × I
Te = 0.83 × 186.67 = 154.93 Nm
```

### 4. Copper Losses
Copper losses in the stator winding (two phases conducting):
```
Pcu = I² × R1L
Pcu = (186.67)² × 0.9 = 31,389.89 W = 31.39 kW
```

### 5. Shaft Torque
Assuming no mechanical losses (friction, windage), the shaft torque equals the electromagnetic torque:
```
Tshaft = Te = 154.93 Nm
```

### 6. Power Analysis
- **Input Power**: Pin = Vdc × I = 600 × 186.67 = 112,000 W = 112 kW
- **Electromagnetic Power**: Pem = EMF_LL × I = 432 × 186.67 = 80,641 W = 80.64 kW
- **Shaft Power**: Pshaft = Pem = 80.64 kW (assuming no mechanical losses)
- **Efficiency**: η = (Pem / Pin) × 100 = (80,641 / 112,000) × 100 = 72.0%

## Results Summary

| Parameter | Value | Unit |
|-----------|-------|------|
| **Line Current** | 186.67 | A |
| **Electromagnetic Torque** | 154.93 | Nm |
| **Shaft Torque** | 154.93 | Nm |
| **Copper Losses** | 31.39 | kW |
| **Input Power** | 112.00 | kW |
| **Shaft Power** | 80.64 | kW |
| **Efficiency** | 72.0 | % |

## Six-Pulse Inverter Operation

### Two-Phase Conduction Mode
In a six-pulse inverter with two phases on at any time:
- At each instant, one phase is connected to the positive DC rail (+Vdc)
- One phase is connected to the negative DC rail (ground)
- The third phase is floating
- This creates six distinct conduction states per electrical cycle
- Each state lasts for 60° of electrical rotation

### Voltage Waveform
The line-to-line voltage is a six-step waveform with amplitude equal to Vdc.

## Visualization Features

The simulation provides 8 interactive visualizations:

1. **Circuit Diagram**: Shows the inverter topology and motor connection
2. **Voltage Waveforms**: Displays line-to-line voltage and back EMF
3. **Current Waveform**: Shows phase current over time
4. **Power Flow**: Visualizes power distribution through the system
5. **Torque Analysis**: Compares electromagnetic and shaft torque
6. **Torque-Speed Characteristic**: Shows how torque varies with speed
7. **Efficiency Curve**: Displays efficiency versus motor speed
8. **Loss Breakdown**: Pie chart showing loss distribution

## Interactive Sliders

Adjust the following parameters in real-time:
- **Vdc**: DC bus voltage (100-1000 V)
- **R1L**: Line-to-line resistance (0.1-5.0 Ω)
- **L1L**: Line-to-line inductance (1.0-20.0 mH)
- **kE**: EMF constant (0.01-0.2 V/rpm)
- **kT**: Torque constant (0.1-2.0 Nm/A)
- **Speed**: Motor speed (1000-10000 rpm)

## Installation and Usage

### Prerequisites
```bash
pip install numpy matplotlib
```

### Running the Simulation
```bash
python pmbm_inverter_simulation.py
```

### Using the Interactive Interface
1. The simulation will open a window with all visualizations
2. Use the sliders at the bottom to adjust parameters
3. All plots update in real-time as you change values
4. Observe how different parameters affect:
   - Motor current
   - Torque production
   - Losses
   - Efficiency
   - Operating characteristics

## Key Observations

### Effect of Speed
- Higher speeds increase back EMF, reducing current and torque
- At no-load speed (EMF = Vdc), current becomes zero
- Efficiency generally improves at higher speeds (lower losses)

### Effect of DC Voltage
- Higher Vdc increases current and torque linearly
- Losses increase quadratically with voltage
- Input power increases, but efficiency may vary

### Effect of Resistance
- Higher resistance reduces current for same voltage
- Increases copper losses significantly
- Reduces efficiency substantially
- Limits maximum torque capability

### Effect of Torque Constant
- Higher kT produces more torque per ampere
- Makes the motor more efficient for same torque output
- Does not affect current (which depends on voltage and resistance)

## Assumptions and Limitations

1. **Steady-State Analysis**: Transient effects are not considered
2. **Ideal Switching**: Switching losses in the inverter are neglected
3. **No Mechanical Losses**: Friction and windage losses are not included
4. **Constant Parameters**: Motor parameters are assumed constant (no saturation effects)
5. **Balanced System**: Three phases are perfectly balanced
6. **Simplified Current Waveform**: Actual current has ripple due to inductance

## Applications

This type of motor-inverter system is commonly used in:
- Electric vehicles and hybrid vehicles
- Industrial servo drives
- Robotics and automation
- HVAC compressors
- Aerospace actuators
- High-performance machine tools

## Further Enhancements

Possible extensions to this simulation:
1. Add mechanical losses (friction, windage)
2. Include core losses (hysteresis and eddy current)
3. Model current ripple due to inductance
4. Add temperature effects on resistance
5. Include magnetic saturation effects
6. Simulate transient response
7. Add PWM modulation for better control

## References

- Power Electronics: Converters, Applications, and Design - Ned Mohan
- Electric Motor Drives: Modeling, Analysis, and Control - R. Krishnan
- Analysis of Electric Machinery and Drive Systems - Paul Krause

## License

This simulation is provided for educational purposes.

---
*Created for advanced electrical networks analysis and motor drive system studies*
