# Advanced DC Motor Duty Cycle Analysis Application

## Overview

This comprehensive Python application solves DC motor duty cycle problems and provides advanced multi-physics simulation capabilities for electrical engineering applications.

## Solved Problem

**Default Duty Cycle Problem:**
A motor has the following duty cycle:
1. Load rising from 200 to 400 H.P. - 4 min.
2. Uniform load 300 H.P. - 2 min.
3. Regenerative braking - H.P. returned to supply from 50 to zero - 1 min.
4. Remaining idle for - 1 min.

**Solution:** The application calculates the RMS motor rating using the duty cycle method.

## Features

### 1. Duty Cycle Analysis
- **RMS Power Calculation**: Accurate RMS power rating calculation for complex duty cycles
- **Multiple Segment Types**: Rising, uniform, regenerative braking, and idle segments
- **Visual Profile**: Real-time visualization of power demand over time
- **Energy Calculation**: Total energy consumption per cycle
- **Safety Factor**: Automatic inclusion of safety margin for motor selection

### 2. Multi-Physics Simulation
- **Electromagnetic Model**: Complete DC motor electromagnetic equations
- **Thermal Model**: Heat transfer and temperature rise calculations
- **Mechanical Model**: Torque, speed, and inertia dynamics
- **Coupled Analysis**: Simultaneous solution of all physics domains

### 3. ODE Solvers
- **RK45**: 4th/5th order Runge-Kutta (default, recommended)
- **RK23**: 2nd/3rd order Runge-Kutta (faster)
- **DOP853**: 8th order Runge-Kutta (high accuracy)
- **Radau**: Implicit solver for stiff systems
- **BDF**: Backward differentiation formulas
- **Euler**: Simple explicit method (educational)

### 4. Loss Analysis
- **Copper Losses**: Armature and field winding losses (temperature-dependent)
- **Iron Losses**: Hysteresis and eddy current losses
- **Mechanical Losses**: Friction and windage
- **Stray Losses**: Additional load-dependent losses
- **Efficiency Tracking**: Real-time efficiency calculation

### 5. Economic Analysis
- **Energy Cost**: Per-cycle and annual energy costs
- **Lifecycle Analysis**: Total cost of ownership over motor lifetime
- **Maintenance Costs**: Scheduled maintenance tracking
- **Component Replacement**: Replacement cost scheduling
- **Cost per Hour**: Operating cost analysis

### 6. Advanced Controls
- **Voltage Control**: PWM, armature voltage, field control
- **Speed Control**: Open-loop, closed-loop, PID
- **Current Limiting**: Automatic overcurrent protection
- **Thermal Derating**: Automatic power reduction on overheating
- **Power Factor**: Power quality tracking

### 7. Mechanical Stress Analysis
- **Torsional Stress**: Shaft stress calculations
- **Bearing Loads**: Radial and thrust load analysis
- **Bending Stress**: Shaft bending analysis
- **Safety Factors**: Mechanical safety verification

### 8. User Interface
- **Tabbed Interface**: Organized workflow across multiple tabs
- **Auto-Scaling**: Automatic window and widget resizing
- **Interactive Plots**: Real-time visualization with matplotlib
- **Input Sliders**: Easy parameter adjustment
- **Progress Tracking**: Simulation progress indication

## Installation

### Requirements
```bash
pip install numpy scipy matplotlib
```

Or use the requirements file:
```bash
pip install -r requirements.txt
```

### Requirements.txt
```
numpy>=1.20.0
scipy>=1.7.0
matplotlib>=3.3.0
```

## Usage

### Quick Start

1. **Run the Application**:
   ```bash
   python motor_duty_cycle_advanced.py
   ```

2. **Load Default Problem**:
   - Application loads the default duty cycle problem automatically
   - Or use Menu → File → Load Default Problem

3. **Calculate RMS Rating**:
   - Go to "Duty Cycle Definition" tab
   - Click "Calculate RMS Rating"
   - View results and recommended motor size

4. **Run Simulation**:
   - Go to "Dynamic Simulation" tab
   - Select ODE solver (RK45 recommended)
   - Click "Start" to run multi-physics simulation

5. **Analyze Results**:
   - View dynamic behavior in "Dynamic Simulation" tab
   - Explore multi-physics coupling in "Multi-Physics" tab
   - Check losses in "Loss Analysis" tab
   - Calculate economics in "Economic Analysis" tab

### Custom Duty Cycle

1. **Clear Default**:
   - Click "Clear All" in Duty Cycle Definition tab

2. **Add Segments**:
   - Click "Add Segment"
   - Enter segment parameters:
     - Name
     - Type (rising/uniform/regenerative/idle)
     - Start power (HP)
     - End power (HP)
     - Duration (minutes)

3. **Calculate**:
   - Click "Calculate RMS Rating"

### Motor Parameters

Configure motor parameters in "Motor Parameters" tab:

**Electrical:**
- Rated voltage (V)
- Armature resistance (Ω)
- Field resistance (Ω)
- Armature inductance (H)
- Maximum current limit (A)

**Mechanical:**
- Rated speed (RPM)
- Moment of inertia (kg·m²)
- Friction coefficient
- Shaft diameter (m)

**Thermal:**
- Ambient temperature (°C)
- Maximum operating temperature (°C)
- Thermal resistance (K/W)
- Thermal capacitance (J/K)

**Efficiency:**
- Rated efficiency
- Loss coefficients

## Application Tabs

### 1. ⚡ Duty Cycle Definition
- Define duty cycle segments
- Calculate RMS power rating
- Visualize power profile
- View energy consumption

### 2. ⚙️ Motor Parameters
- Configure all motor parameters
- Use sliders for easy adjustment
- Update motor model

### 3. 🔬 Dynamic Simulation
- Select ODE solver
- Run real-time simulation
- View speed, current, power, temperature, torque
- Start/Stop/Reset controls

### 4. 🌡️ Multi-Physics
- 3D phase space visualization
- Electromagnetic coupling (Current-Torque)
- Thermal coupling (Temperature-Loss)
- Mechanical coupling (Speed-Torque)

### 5. 📊 Loss Analysis
- Stacked area chart of losses
- Individual loss components
- Pie chart of average distribution
- Instantaneous efficiency

### 6. 💰 Economic Analysis
- Energy cost per cycle
- Annual operating costs
- Lifetime cost analysis
- Cost breakdown visualization

### 7. 🎛️ Advanced Controls
- Control method selection
- Power consumption tracking
- Cumulative energy
- Real-time cost calculation

## Mathematical Models

### RMS Power Calculation

For a duty cycle with segments, the RMS power is:

```
P_RMS = sqrt(Σ(P_i² × t_i) / Σ(t_i))
```

For linearly rising power:
```
P_RMS_segment = sqrt((P₁² + P₁×P₂ + P₂²) / 3)
```

### Differential Equations

The multi-physics model solves:

**Electrical:**
```
L_a × dI/dt = V - E_b - I × R_a
```

**Electromagnetic:**
```
T_em = k_φ × I_a
E_b = k_φ × ω
```

**Mechanical:**
```
J × dω/dt = T_em - T_friction
```

**Thermal:**
```
C_th × dT/dt = P_loss - (T - T_amb)/R_th
```

### Loss Models

**Copper Losses:**
```
P_cu = I² × R_a(T)
R_a(T) = R_a0 × (1 + α × (T - T_0))
```

**Iron Losses:**
```
P_iron ∝ f^1.3 × B²
```

**Mechanical Losses:**
```
P_mech = k_f × ω²
```

## Output Files

The application can save:

1. **duty_cycle_results.txt**: RMS calculation results
2. **economic_results.txt**: Economic analysis
3. **simulation_data.csv**: Time-series simulation data
   - Columns: Time, Speed, Current, Torque, Power, Temperature

## Advanced Features

### Real-Time Simulation
- Background threading for responsive UI
- Progress bar indication
- Status updates
- Error handling

### Auto-Scaling GUI
- Window resizes automatically
- Plots scale with window size
- Optimized for different screen sizes

### Thermal Protection
- Automatic detection of overheating
- Derating factor calculation
- Warning messages
- Current limiting

### Practical Engineering Use

This application is designed for:
- **Motor Selection**: Choosing appropriate motor ratings
- **Duty Cycle Analysis**: Understanding load patterns
- **Thermal Analysis**: Ensuring safe operating temperatures
- **Economic Evaluation**: Total cost of ownership
- **Control Design**: Evaluating control strategies
- **Educational**: Learning motor dynamics

## Example Results

For the default problem (200→400 HP, 300 HP, 50→0 HP braking, idle):

- **RMS Power**: ~297 HP
- **Recommended Rating**: ~342 HP (with 15% safety factor)
- **Peak Power**: 400 HP
- **Total Cycle Energy**: Variable based on duration
- **Cycle Time**: 8 minutes

## Troubleshooting

### Simulation Errors
- Check that duty cycle is defined
- Ensure motor parameters are reasonable
- Try different ODE solver
- Reduce simulation time step

### Performance
- Use RK45 for best balance
- Reduce time resolution for faster results
- Close other applications for complex simulations

### Display Issues
- Resize window to refresh plots
- Check screen resolution settings
- Use fullscreen mode for best view

## Technical Specifications

- **Language**: Python 3.7+
- **GUI Framework**: Tkinter
- **Numerical Computing**: NumPy, SciPy
- **Visualization**: Matplotlib
- **Architecture**: Object-oriented with MVC pattern

## Code Structure

```
motor_duty_cycle_advanced.py
├── DutyCycleSegment (dataclass)
├── MotorParameters (dataclass)
├── DutyCycleCalculator
│   ├── calculate_rms_power()
│   └── generate_duty_cycle_profile()
├── AdvancedMotorModel
│   ├── calculate_losses()
│   ├── calculate_efficiency()
│   └── mechanical_stress_analysis()
├── MultiPhysicsSimulator
│   ├── coupled_differential_equations()
│   ├── simulate_scipy()
│   └── simulate_euler()
├── EconomicAnalyzer
│   ├── analyze_energy_cost()
│   └── lifecycle_cost_analysis()
└── MotorDutyCycleGUI
    ├── setup_*_tab() methods
    └── display_*() methods
```

## References

- Electric Machinery Fundamentals (Chapman)
- DC Motor Theory and Practice
- Multi-Physics Simulation Methods
- Power Electronics and Motor Drives

## License

Open source for educational and professional use.

## Author

Advanced electrical engineering analysis tool for practical motor applications.

## Version History

- **v2.0**: Complete rewrite with multi-physics simulation
- **v1.0**: Basic duty cycle calculator

## Support

For issues or questions:
1. Check this README
2. Review example problems
3. Verify input parameters
4. Check console for error messages

---

**Note**: This application uses RMS values for all voltage and current calculations in the simulation models, ensuring accurate thermal and electrical analysis.
