# Quick Start Guide - Motor Duty Cycle Calculator

## Problem Solved

**A motor has following duty cycle:**
- Load rising from 200 to 400 H.P. - 4 min.
- Uniform load 300 H.P. - 2 min.
- Regenerative braking - H.P. returned to supply from 50 to zero - 1 min.
- Remaining idle for - 1 min.

**Solution: 302.7 HP (226 kW) motor recommended**

## Installation

```bash
# Install dependencies
pip install numpy scipy matplotlib

# Or use requirements file
pip install -r requirements.txt
```

## Run the Application

```bash
python motor_duty_cycle_advanced.py
```

## Run Tests Only

```bash
python test_duty_cycle.py
```

## Features Included

✓ **Duty Cycle RMS Calculation**
- Automatically calculates RMS power rating
- Includes safety factor
- Visual power profile

✓ **Multi-Physics Simulation**
- Electromagnetic model
- Thermal model with heat transfer
- Mechanical dynamics
- Coupled differential equations

✓ **ODE Solvers**
- RK45 (Runge-Kutta 4/5th order) - Default
- RK23, DOP853, Radau, BDF
- Euler method

✓ **Advanced Analysis**
- Detailed loss breakdown (copper, iron, friction, stray)
- Efficiency tracking
- Economic analysis
- Lifecycle costs
- Power consumption tracking

✓ **Advanced Controls**
- PWM voltage control
- Speed control (open/closed loop, PID)
- Current limiting
- Thermal derating

✓ **Mechanical Stress**
- Torsional stress
- Bearing loads
- Shaft analysis

✓ **GUI Features**
- Tabbed interface
- Auto-scaling
- Real-time plots
- Interactive sliders
- Start/Stop/Reset controls

## Quick Usage

1. **Launch Application**
   ```bash
   python motor_duty_cycle_advanced.py
   ```

2. **Calculate RMS Rating**
   - Tab: "Duty Cycle Definition"
   - Click "Calculate RMS Rating"
   - Result: ~303 HP motor recommended

3. **Run Simulation**
   - Tab: "Dynamic Simulation"
   - Select solver: RK45
   - Click "Start"
   - View results in all tabs

4. **Economic Analysis**
   - Tab: "Economic Analysis"
   - Set parameters (electricity rate, operating hours)
   - Click "Calculate Economics"

## Key Results for Default Problem

| Parameter | Value |
|-----------|-------|
| RMS Power | 263.2 HP (196.3 kW) |
| Peak Power | 400 HP (298.4 kW) |
| **Recommended Motor** | **302.7 HP (225.8 kW)** |
| Safety Factor | 15% |
| Cycle Time | 8 minutes |

## Technical Highlights

### RMS Calculation Method
```
For linearly varying load:
P_RMS = sqrt((P1² + P1×P2 + P2²) / 3)

For overall cycle:
P_RMS = sqrt(Σ(P_segment² × t_segment) / Σ(t_segment))
```

### Differential Equations
```
Electrical:  L·dI/dt = V - E_b - I·R
Mechanical:  J·dω/dt = T_em - T_friction
Thermal:     C·dT/dt = P_loss - (T-T_amb)/R_th
```

### Multi-Physics Coupling
- Current → Torque (Electromagnetic)
- Loss → Temperature (Thermal)
- Torque → Speed (Mechanical)
- Temperature → Resistance (Feedback)

## File Structure

```
motor_duty_cycle_advanced.py  ← Main application
test_duty_cycle.py            ← Test calculations
README_DUTY_CYCLE.md          ← Full documentation
QUICKSTART.md                 ← This file
requirements.txt              ← Python dependencies
```

## Troubleshooting

**"No module named 'tkinter'"**
- Install: `sudo apt-get install python3-tk` (Linux)
- Or: Use test_duty_cycle.py for calculations only

**Simulation takes long time**
- Use RK45 instead of DOP853
- Reduce simulation time
- Increase max_step parameter

**Window too small**
- Maximize window
- Resize to fit screen
- Auto-scaling enabled

## Advanced Features

### Custom Duty Cycle
1. Click "Clear All"
2. Click "Add Segment" for each phase
3. Enter power and duration
4. Calculate RMS

### Motor Parameters
- Adjust all electrical/mechanical/thermal parameters
- Use sliders for easy tuning
- Update motor model

### Save Results
- Menu → File → Save Results
- Creates .txt and .csv files
- Includes all analysis data

## Support

Check the full README_DUTY_CYCLE.md for:
- Complete documentation
- Mathematical models
- Example calculations
- Advanced features

## Summary

This application provides a complete solution for:
1. ✓ Duty cycle problem solved (303 HP motor)
2. ✓ Python + Tkinter GUI with tabs
3. ✓ Real-time ODE solvers (RK45, Euler)
4. ✓ Multi-physics simulation
5. ✓ Economic analysis
6. ✓ Advanced controls
7. ✓ Thermal derating
8. ✓ Auto-scaling interface
9. ✓ No syntax errors
10. ✓ Practical engineering tool

---

**Ready to use for electrical engineering applications!**
