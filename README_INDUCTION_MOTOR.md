# Advanced Induction Motor Analysis Tool

## Overview
Comprehensive Python + Tkinter application for solving Example 6.3 and performing advanced induction motor analysis with multi-physics simulation capabilities.

## Features

### 1. Example 6.3 Solution
- Automatic calculation of starting current and torque at rated frequency
- Starting values at minimum (5 Hz) and maximum (75 Hz) frequencies
- Breakdown torque vs frequency curve with V/f constant control
- Real-time RMS current and voltage calculations

### 2. Motor Parameters
- Complete equivalent circuit parameters (R1, R2', X1, X2', Xm)
- Ratings configuration (power, voltage, speed, frequency, poles)
- Delta or Star connection support
- Mechanical parameters (inertia, friction)
- Thermal parameters (resistance, capacitance, ambient temperature)

### 3. Control Methods
- **V/f Constant Control**: Classic voltage/frequency control with boost
- **Field Oriented Control (FOC)**: Decoupled flux and torque control
- **Direct Torque Control (DTC)**: Hysteresis-based torque control
- **Energy Optimization**: Flux optimization for minimum losses
- Soft-start capability with programmable ramp
- Real-time frequency, voltage, and load torque adjustment

### 4. Dynamic Simulation
- **RK45 Solver**: High-accuracy adaptive Runge-Kutta method
- **Euler Solver**: Fast fixed-step integration
- Real-time visualization of:
  - Speed vs time
  - Torque vs time
  - Current vs time (RMS values)
  - Temperature vs time
- Configurable simulation time
- Start/Stop/Reset controls with progress indication

### 5. Multi-Physics Simulation
#### Electromagnetic Analysis
- Detailed loss breakdown:
  - Copper losses (stator and rotor) - temperature dependent
  - Iron losses (hysteresis and eddy current)
  - Mechanical losses (friction and windage)
  - Stray load losses
- Efficiency calculations

#### Thermal Analysis
- Three-node lumped parameter thermal model (stator, rotor, frame)
- Heat transfer equations solved simultaneously with electrical equations
- Temperature distribution visualization
- Class F insulation limit monitoring (155°C)
- Thermal capacitance and resistance modeling

#### Mechanical Stress Analysis
- Shaft torque and stress calculations
- Bearing load analysis (radial, axial, dynamic)
- Transient torque evaluation

#### Derating Analysis
- Temperature derating factors
- Altitude derating (above 1000m)
- Voltage variation derating
- Overall derating factor calculation

### 6. Economic Analysis
#### Energy Consumption
- Annual kWh consumption calculation
- Operating cost analysis
- Load factor and efficiency impact

#### Lifecycle Cost (LCC)
- Initial investment cost
- Present value of operating costs (5% discount rate)
- Maintenance costs over lifetime
- Total cost of ownership
- Cost distribution breakdown

#### Payback Analysis
- Simple payback period for motor replacement
- Efficiency improvement benefits
- Investment recommendations
- Comparative cost analysis

### 7. Advanced Features
- **Auto-scaling GUI**: Responsive interface that adjusts to window size
- **Real-time calculations**: Instant feedback on parameter changes
- **Multi-tab interface**: Organized workflow
- **Scrollable parameters**: Easy access to all settings
- **Export capabilities**: Save results for documentation
- **Professional formatting**: Clear, readable output with units

## Installation

### Requirements
```bash
pip install numpy scipy matplotlib tkinter
```

### Running the Application
```bash
python3 induction_motor_analysis.py
```

Or make it executable:
```bash
chmod +x induction_motor_analysis.py
./induction_motor_analysis.py
```

## Motor Specifications (Example 6.3)
- **Power**: 7.5 kW
- **Voltage**: 380 V (line-to-line, Δ-connected)
- **Speed**: 1450 rpm (rated)
- **Frequency**: 50 Hz (rated)
- **Poles**: 4
- **Equivalent Circuit**:
  - R1 = 2.144 Ω (stator resistance)
  - R2' = 1.323 Ω (rotor resistance referred to stator)
  - X1 = 2.891 Ω (stator leakage reactance)
  - X2' = 5.487 Ω (rotor leakage reactance referred to stator)
  - Xm = 116.3 Ω (magnetizing reactance)

## Usage Guide

### Solving Example 6.3
1. Open the "Example 6.3 Solution" tab
2. Click "Solve Example 6.3" button
3. View detailed results in the text area
4. Analyze the breakdown torque curve in the plot

### Running Dynamic Simulation
1. Navigate to "Dynamic Simulation" tab
2. Select solver (RK45 for accuracy, Euler for speed)
3. Set simulation time
4. Click "Start" to begin simulation
5. Monitor real-time plots
6. Use "Stop" to pause, "Reset" to clear

### Multi-Physics Analysis
1. Go to "Multi-Physics Analysis" tab
2. Set operating speed
3. Click "Run Multi-Physics Analysis"
4. Review:
   - Loss breakdown (copper, iron, mechanical, stray)
   - Temperature distribution
   - Mechanical stress
   - Derating factors

### Economic Analysis
1. Open "Economic Analysis" tab
2. Enter operating conditions:
   - Hours per year
   - Load factor
   - Efficiency
   - Lifetime
3. Click "Calculate Economics"
4. Review energy consumption and lifecycle cost
5. Perform payback analysis for motor replacement

### Adjusting Control
1. Select "Control" tab
2. Choose control method
3. Adjust sliders for:
   - Frequency (5-75 Hz)
   - Voltage (0-450 V)
   - Load torque (0-100 Nm)
4. Click "Calculate" for real-time analysis

## Technical Details

### ODE Solver Implementation
The dynamic simulation uses state-space representation:
- States: [ω, θ, T_temp]
  - ω: Rotor angular velocity (rad/s)
  - θ: Rotor position (rad)
  - T_temp: Temperature (°C)

### Thermal Model
Three-node lumped parameter model with:
- Thermal resistances between nodes
- Thermal capacitances for each node
- Power dissipation sources
- Steady-state and transient solutions

### Loss Calculations
- **Copper losses**: I²R with temperature correction (α = 0.00393/°C)
- **Iron losses**: Steinmetz equation (P = k_h·f·B² + k_e·f²·B²)
- **Mechanical losses**: Speed-dependent friction and windage
- **Stray losses**: Approximated as 1% of output power

### Control Methods
- **V/f**: Maintains constant flux by linear V/f relationship
- **FOC**: PI speed controller with d-q axis current commands
- **DTC**: Hysteresis comparators for torque and flux control

## Output Examples

### Example 6.3 Results
```
(a) Starting values at 50 Hz:
    Current (line): XX.XX A (RMS)
    Torque: XX.XX Nm

(b) Starting values at 5 Hz and 75 Hz:
    5 Hz: I = XX.XX A, T = XX.XX Nm
    75 Hz: I = XX.XX A, T = XX.XX Nm

(c) Breakdown torque curve from 5-75 Hz
```

### Loss Breakdown
```
Copper Losses:
  Stator: XXX.XX W
  Rotor: XXX.XX W
Iron Losses:
  Hysteresis: XX.XX W
  Eddy Current: XX.XX W
Mechanical Losses:
  Friction: XX.XX W
  Windage: XX.XX W
Total Losses: XXX.XX W
Efficiency: XX.XX%
```

## Practical Applications
- Motor selection and sizing
- Drive system design
- Energy audit and optimization
- Motor replacement justification
- Thermal management design
- Predictive maintenance planning
- Educational demonstrations

## Validation
All calculations use:
- RMS values for voltage and current
- Per-phase equivalent circuit
- IEEE standard motor parameters
- Temperature-dependent resistances
- Accurate slip calculations

## Notes
- All RMS values are used in simulations as specified
- Delta connection: Line current = √3 × Phase current
- Temperature limits follow Class F insulation (155°C)
- Economic analysis uses 5% discount rate
- Derating factors follow NEMA standards

## Troubleshooting
- If GUI doesn't appear: Check tkinter installation
- If plots don't update: Ensure matplotlib backend is configured
- For slow simulations: Use Euler solver or reduce simulation time
- For convergence issues: Check motor parameters are realistic

## Author
Electrical Engineering Department

## License
Educational and research use

## Version
1.0 - Complete implementation with all requested features
