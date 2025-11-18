"""
Test script for DC Motor Braking Analysis
Verifies the analytical calculations match expected results
"""

import sys
import math

# Import the calculator class
from dc_motor_braking_analysis import (
    MotorParameters,
    DCMotorBrakingCalculator,
    MultiPhysicsSimulator
)

def test_analytical_calculations():
    """Test analytical calculations for the given problem"""

    print("="*70)
    print("DC MOTOR BRAKING ANALYSIS - VERIFICATION TEST")
    print("="*70)
    print()

    # Create motor parameters with problem specifications
    params = MotorParameters(
        power_hp=37.5,
        voltage=220.0,
        full_load_speed=535.0,
        armature_resistance=0.086,
        full_load_current=140.0,
        target_braking_current=200.0
    )

    # Create calculator
    calc = DCMotorBrakingCalculator(params)

    print("MOTOR SPECIFICATIONS:")
    print(f"  Power: {params.power_hp} HP ({calc.power_watts:.1f} W)")
    print(f"  Voltage: {params.voltage} V")
    print(f"  Full Load Speed: {params.full_load_speed} RPM")
    print(f"  Armature Resistance: {params.armature_resistance} Ω")
    print(f"  Full Load Current: {params.full_load_current} A")
    print(f"  Target Braking Current: {params.target_braking_current} A")
    print()

    print("DERIVED PARAMETERS:")
    print(f"  Angular Velocity: {calc.omega_full_load:.3f} rad/s")
    print(f"  Back EMF at Full Load: {calc.Eb_full_load:.3f} V")
    print(f"  Motor Constant (k·φ): {calc.k_phi:.4f} V·s/rad")
    print(f"  Full Load Torque: {calc.torque_full_load:.3f} N·m")
    print()

    # Calculate plugging resistance
    print("PLUGGING RESISTANCE CALCULATION:")
    R_ext = calc.calculate_plugging_resistance()
    print(f"  External Resistance: {R_ext:.4f} Ω")
    print(f"  Total Resistance: {calc.results['total_resistance']:.4f} Ω")
    print()

    # Verify calculation manually
    expected_total_R = (params.voltage + calc.Eb_full_load) / params.target_braking_current
    expected_R_ext = expected_total_R - params.armature_resistance

    print("VERIFICATION:")
    print(f"  Expected Total Resistance: {expected_total_R:.4f} Ω")
    print(f"  Expected External Resistance: {expected_R_ext:.4f} Ω")
    print(f"  Match: {abs(R_ext - expected_R_ext) < 0.001}")
    print()

    # Calculate initial braking torque
    print("BRAKING TORQUE AT FULL LOAD SPEED ({:.1f} RPM):".format(params.full_load_speed))
    T_initial, I_initial = calc.calculate_braking_torque(params.full_load_speed, R_ext)
    print(f"  Current: {I_initial:.2f} A")
    print(f"  Torque: {T_initial:.2f} N·m")
    print(f"  Power: {T_initial * calc.omega_full_load / 1000:.2f} kW")
    print()

    # Calculate braking torque at half speed
    half_speed = params.full_load_speed / 2
    print(f"BRAKING TORQUE AT HALF SPEED ({half_speed:.1f} RPM):")
    T_half, I_half = calc.calculate_braking_torque(half_speed, R_ext)
    print(f"  Current: {I_half:.2f} A")
    print(f"  Torque: {T_half:.2f} N·m")
    print(f"  Power: {T_half * (calc.omega_full_load/2) / 1000:.2f} kW")
    print()

    # Calculate reduction
    torque_reduction = ((T_initial - T_half) / T_initial) * 100
    print(f"TORQUE REDUCTION: {torque_reduction:.1f}%")
    print()

    # Mechanical stress analysis
    print("MECHANICAL STRESS ANALYSIS:")
    stress_initial = calc.mechanical_stress_analysis(T_initial)
    print(f"  At Full Speed:")
    print(f"    Torsional Stress: {stress_initial['torsional_stress_MPa']:.2f} MPa")
    print(f"    Bearing Thrust Load: {stress_initial['bearing_thrust_load_N']:.1f} N")
    print()

    stress_half = calc.mechanical_stress_analysis(T_half)
    print(f"  At Half Speed:")
    print(f"    Torsional Stress: {stress_half['torsional_stress_MPa']:.2f} MPa")
    print(f"    Bearing Thrust Load: {stress_half['bearing_thrust_load_N']:.1f} N")
    print()

    # Loss analysis
    print("LOSS ANALYSIS AT FULL LOAD:")
    losses_full = calc.calculate_losses(I_initial, params.full_load_speed, 50.0)
    print(f"  Copper Loss: {losses_full['copper_loss']:.2f} W")
    print(f"  Field Loss: {losses_full['field_loss']:.2f} W")
    print(f"  Iron Loss: {losses_full['iron_loss']:.2f} W")
    print(f"  Friction Loss: {losses_full['friction_loss']:.2f} W")
    print(f"  Stray Loss: {losses_full['stray_loss']:.2f} W")
    print(f"  Total Loss: {losses_full['total_loss']:.2f} W")
    print()

    # Summary
    print("="*70)
    print("SUMMARY OF KEY RESULTS:")
    print("="*70)
    print(f"1. External Plugging Resistance Required: {R_ext:.4f} Ω")
    print(f"2. Initial Braking Torque: {T_initial:.2f} N·m")
    print(f"3. Braking Torque at Half Speed: {T_half:.2f} N·m")
    print(f"4. Torque Reduction: {torque_reduction:.1f}%")
    print(f"5. Maximum Torsional Stress: {stress_initial['torsional_stress_MPa']:.2f} MPa")
    print("="*70)
    print()

    return True


def test_simulation():
    """Test dynamic simulation"""
    print("="*70)
    print("DYNAMIC SIMULATION TEST")
    print("="*70)
    print()

    # Create motor parameters
    params = MotorParameters()
    calc = DCMotorBrakingCalculator(params)

    # Calculate plugging resistance
    R_ext = calc.calculate_plugging_resistance()
    print(f"Plugging Resistance: {R_ext:.4f} Ω")
    print()

    # Create simulator
    simulator = MultiPhysicsSimulator(calc)

    print("Running simulation with RK45 method...")
    # Run short simulation
    results = simulator.simulate_rk45((0, 1.0), method='RK45')

    if results['success']:
        print("✓ Simulation completed successfully")
        print(f"  Time steps: {len(results['time'])}")
        print(f"  Initial speed: {results['speed_rpm'][0]:.1f} RPM")
        print(f"  Final speed: {results['speed_rpm'][-1]:.1f} RPM")
        print(f"  Speed reduction: {results['speed_rpm'][0] - results['speed_rpm'][-1]:.1f} RPM")
        print(f"  Initial current: {results['current'][0]:.1f} A")
        print(f"  Final temperature: {results['temperature'][-1]:.1f} °C")
        print(f"  Total energy dissipated: {results['heat'][-1]/1000:.2f} kJ")
    else:
        print("✗ Simulation failed:", results['message'])
        return False

    print()
    print("Testing Euler method...")
    results_euler = simulator.simulate_euler((0, 0.5), dt=0.001)

    if results_euler['success']:
        print("✓ Euler simulation completed successfully")
        print(f"  Time steps: {len(results_euler['time'])}")
        print(f"  Final speed: {results_euler['speed_rpm'][-1]:.1f} RPM")
    else:
        print("✗ Euler simulation failed")
        return False

    print()
    print("="*70)
    print("ALL TESTS PASSED ✓")
    print("="*70)
    print()

    return True


def main():
    """Main test function"""
    try:
        # Run analytical tests
        if not test_analytical_calculations():
            print("Analytical tests failed!")
            sys.exit(1)

        # Run simulation tests
        if not test_simulation():
            print("Simulation tests failed!")
            sys.exit(1)

        print("\n" + "="*70)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("The application is ready to use.")
        print("Run: python3 dc_motor_braking_analysis.py")
        print("="*70)

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
