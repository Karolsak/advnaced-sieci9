"""
DC Motor Braking Calculations Module
Core calculation engine without GUI dependencies
"""

import numpy as np
from scipy.integrate import solve_ivp
import math
from dataclasses import dataclass
from typing import Tuple, Dict


@dataclass
class MotorParameters:
    """DC Motor Parameters"""
    power_hp: float = 37.5  # HP
    voltage: float = 220.0  # V
    full_load_speed: float = 535.0  # rpm
    armature_resistance: float = 0.086  # Ohm
    full_load_current: float = 140.0  # A
    target_braking_current: float = 200.0  # A
    moment_of_inertia: float = 0.5  # kg.m^2
    field_resistance: float = 100.0  # Ohm
    ambient_temp: float = 25.0  # Celsius
    thermal_resistance: float = 2.0  # K/W
    thermal_capacitance: float = 500.0  # J/K
    friction_coefficient: float = 0.01  # N.m.s/rad


class DCMotorBrakingCalculator:
    """Core calculation engine for DC motor braking analysis"""

    def __init__(self, params: MotorParameters):
        self.params = params
        self.results = {}
        self._calculate_derived_parameters()

    def _calculate_derived_parameters(self):
        """Calculate derived motor parameters"""
        p = self.params

        # Convert speed to rad/s
        self.omega_full_load = p.full_load_speed * 2 * math.pi / 60

        # Calculate back EMF at full load
        self.Eb_full_load = p.voltage - p.full_load_current * p.armature_resistance

        # Calculate motor constant (k*phi)
        self.k_phi = self.Eb_full_load / self.omega_full_load

        # Calculate power in watts
        self.power_watts = p.power_hp * 746  # 1 HP = 746 W

        # Calculate full load torque
        self.torque_full_load = self.power_watts / self.omega_full_load

    def calculate_plugging_resistance(self) -> float:
        """Calculate external resistance for plugging"""
        p = self.params

        # At plugging: (V + Eb) = I * (Ra + R_ext)
        # Eb at full load speed
        total_voltage = p.voltage + self.Eb_full_load

        # Total resistance needed
        total_resistance = total_voltage / p.target_braking_current

        # External resistance
        R_ext = total_resistance - p.armature_resistance

        self.results['plugging_resistance'] = R_ext
        self.results['total_resistance'] = total_resistance

        return R_ext

    def calculate_braking_torque(self, speed_rpm: float, R_ext: float) -> Tuple[float, float]:
        """Calculate braking torque and current at given speed"""
        p = self.params

        # Convert speed to rad/s
        omega = speed_rpm * 2 * math.pi / 60

        # Back EMF at this speed
        Eb = self.k_phi * omega

        # Current during plugging
        current = (p.voltage + Eb) / (p.armature_resistance + R_ext)

        # Braking torque
        torque = self.k_phi * current

        return torque, current

    def calculate_losses(self, current: float, speed_rpm: float, temp: float) -> Dict[str, float]:
        """Calculate detailed loss breakdown"""
        p = self.params
        omega = speed_rpm * 2 * math.pi / 60

        # Copper losses (I^2 * R) - temperature dependent
        temp_coefficient = 0.00393  # Copper temp coefficient
        Ra_temp = p.armature_resistance * (1 + temp_coefficient * (temp - 25))
        copper_loss = current**2 * Ra_temp

        # Field copper loss
        field_current = p.voltage / p.field_resistance
        field_loss = field_current**2 * p.field_resistance

        # Iron losses (hysteresis + eddy current)
        iron_loss = 0.02 * (abs(speed_rpm) / 1000)**1.5 * p.voltage**2 / 10000

        # Mechanical friction losses
        friction_loss = p.friction_coefficient * omega**2

        # Stray load losses (approximation: 1% of output power)
        stray_loss = 0.01 * abs(current * p.voltage)

        total_loss = copper_loss + field_loss + iron_loss + friction_loss + stray_loss

        return {
            'copper_loss': copper_loss,
            'field_loss': field_loss,
            'iron_loss': iron_loss,
            'friction_loss': friction_loss,
            'stray_loss': stray_loss,
            'total_loss': total_loss
        }

    def mechanical_stress_analysis(self, torque: float) -> Dict[str, float]:
        """Analyze mechanical stress on shaft and bearings"""
        shaft_diameter = 0.05  # meters (50mm assumed)

        # Torsional shear stress: τ = (16 * T) / (π * d^3)
        torsional_stress = (16 * abs(torque)) / (math.pi * shaft_diameter**3)

        # Bearing load (simplified)
        bearing_radial_load = 500  # N (assumed)
        bearing_thrust_load = abs(torque) / (shaft_diameter / 2)

        return {
            'torsional_stress_MPa': torsional_stress / 1e6,
            'bearing_radial_load_N': bearing_radial_load,
            'bearing_thrust_load_N': bearing_thrust_load,
            'shaft_diameter_mm': shaft_diameter * 1000
        }


class MultiPhysicsSimulator:
    """Advanced multi-physics simulation engine"""

    def __init__(self, calculator: DCMotorBrakingCalculator):
        self.calc = calculator
        self.params = calculator.params

    def coupled_equations(self, t: float, y: np.ndarray) -> np.ndarray:
        """
        Coupled electromagnetic-thermal-mechanical differential equations
        State vector y = [omega, theta, I_a, T_motor, Q_heat]
        """
        omega, theta, I_a, T_motor, Q_heat = y

        p = self.params
        speed_rpm = omega * 60 / (2 * math.pi)

        # Back EMF
        Eb = self.calc.k_phi * omega

        # Get external resistance
        R_ext = self.calc.results.get('plugging_resistance', 0)

        # Voltage application (reversed during plugging)
        if omega > 0:
            V_applied = -p.voltage
        else:
            V_applied = 0

        # Temperature-dependent resistance
        temp_coefficient = 0.00393
        Ra_temp = p.armature_resistance * (1 + temp_coefficient * (T_motor - 25))

        # Current derivative
        tau_electrical = 0.01
        I_target = (V_applied - Eb) / (Ra_temp + R_ext) if (Ra_temp + R_ext) > 0 else 0
        dI_dt = (I_target - I_a) / tau_electrical

        # Electromagnetic torque
        T_em = self.calc.k_phi * I_a

        # Load torque (braking)
        T_load = -T_em if omega > 0 else 0

        # Friction torque
        T_friction = p.friction_coefficient * omega

        # Mechanical equation
        domega_dt = (T_load - T_friction) / p.moment_of_inertia

        # Angular position
        dtheta_dt = omega

        # Thermal equations
        losses = self.calc.calculate_losses(I_a, speed_rpm, T_motor)
        P_loss = losses['total_loss']

        Q_dissipated = (T_motor - p.ambient_temp) / p.thermal_resistance
        dT_dt = (P_loss - Q_dissipated) / p.thermal_capacitance

        # Heat accumulation
        dQ_dt = P_loss

        # Stop when motor stops
        if omega <= 0 and domega_dt <= 0:
            domega_dt = 0
            dtheta_dt = 0
            dI_dt = 0

        return np.array([domega_dt, dtheta_dt, dI_dt, dT_dt, dQ_dt])

    def simulate_rk45(self, t_span: Tuple[float, float], method='RK45') -> Dict:
        """Run simulation using scipy's solve_ivp"""
        # Initial conditions
        omega_0 = self.calc.omega_full_load
        theta_0 = 0
        I_a_0 = self.params.full_load_current
        T_motor_0 = self.params.ambient_temp + 20
        Q_heat_0 = 0

        y0 = np.array([omega_0, theta_0, I_a_0, T_motor_0, Q_heat_0])

        # Solve ODE
        sol = solve_ivp(
            self.coupled_equations,
            t_span,
            y0,
            method=method,
            max_step=0.01,
            dense_output=True
        )

        # Extract results
        results = {
            'time': sol.t,
            'omega': sol.y[0, :],
            'speed_rpm': sol.y[0, :] * 60 / (2 * math.pi),
            'theta': sol.y[1, :],
            'current': sol.y[2, :],
            'temperature': sol.y[3, :],
            'heat': sol.y[4, :],
            'success': sol.success,
            'message': sol.message
        }

        # Calculate derived quantities
        results['torque'] = self.calc.k_phi * results['current']
        results['power'] = results['torque'] * results['omega']

        # Calculate losses at each time step
        losses_history = []
        for i in range(len(results['time'])):
            losses = self.calc.calculate_losses(
                results['current'][i],
                results['speed_rpm'][i],
                results['temperature'][i]
            )
            losses_history.append(losses)

        results['losses'] = losses_history

        return results


def print_analysis_report(params: MotorParameters):
    """Generate comprehensive analysis report"""

    print("="*70)
    print("DC MOTOR BRAKING ANALYSIS - COMPREHENSIVE REPORT")
    print("="*70)
    print()

    # Create calculator
    calc = DCMotorBrakingCalculator(params)

    print("MOTOR SPECIFICATIONS:")
    print(f"  Power Rating:           {params.power_hp:.1f} HP ({calc.power_watts:.1f} W)")
    print(f"  Voltage:                {params.voltage:.1f} V")
    print(f"  Full Load Speed:        {params.full_load_speed:.1f} RPM ({calc.omega_full_load:.2f} rad/s)")
    print(f"  Armature Resistance:    {params.armature_resistance:.4f} Ω")
    print(f"  Full Load Current:      {params.full_load_current:.1f} A")
    print(f"  Target Braking Current: {params.target_braking_current:.1f} A")
    print()

    print("DERIVED PARAMETERS:")
    print(f"  Back EMF (Full Load):   {calc.Eb_full_load:.2f} V")
    print(f"  Motor Constant (k·φ):   {calc.k_phi:.4f} V·s/rad")
    print(f"  Full Load Torque:       {calc.torque_full_load:.2f} N·m")
    print()

    # Calculate plugging resistance
    R_ext = calc.calculate_plugging_resistance()

    print("="*70)
    print("PLUGGING RESISTANCE CALCULATION:")
    print("="*70)
    print(f"  External Resistance Required:  {R_ext:.4f} Ω")
    print(f"  Total Circuit Resistance:      {calc.results['total_resistance']:.4f} Ω")
    print()

    # Calculate initial braking torque
    T_initial, I_initial = calc.calculate_braking_torque(params.full_load_speed, R_ext)

    print("="*70)
    print("BRAKING TORQUE ANALYSIS:")
    print("="*70)
    print()
    print(f"INITIAL BRAKING (At Full Load Speed = {params.full_load_speed:.1f} RPM):")
    print(f"  Braking Current:        {I_initial:.2f} A")
    print(f"  Braking Torque:         {T_initial:.2f} N·m")
    print(f"  Braking Power:          {T_initial * calc.omega_full_load / 1000:.2f} kW")
    print()

    # Calculate braking torque at half speed
    half_speed = params.full_load_speed / 2
    T_half, I_half = calc.calculate_braking_torque(half_speed, R_ext)

    print(f"AT HALF SPEED ({half_speed:.1f} RPM):")
    print(f"  Braking Current:        {I_half:.2f} A")
    print(f"  Braking Torque:         {T_half:.2f} N·m")
    print(f"  Braking Power:          {T_half * (calc.omega_full_load/2) / 1000:.2f} kW")
    print()

    torque_reduction = ((T_initial - T_half) / T_initial) * 100
    print(f"TORQUE REDUCTION:         {torque_reduction:.1f}%")
    print()

    # Mechanical stress analysis
    stress_initial = calc.mechanical_stress_analysis(T_initial)
    stress_half = calc.mechanical_stress_analysis(T_half)

    print("="*70)
    print("MECHANICAL STRESS ANALYSIS:")
    print("="*70)
    print()
    print("INITIAL CONDITIONS:")
    print(f"  Torsional Stress:       {stress_initial['torsional_stress_MPa']:.2f} MPa")
    print(f"  Bearing Radial Load:    {stress_initial['bearing_radial_load_N']:.1f} N")
    print(f"  Bearing Thrust Load:    {stress_initial['bearing_thrust_load_N']:.1f} N")
    print(f"  Shaft Diameter:         {stress_initial['shaft_diameter_mm']:.1f} mm")
    print()
    print("AT HALF SPEED:")
    print(f"  Torsional Stress:       {stress_half['torsional_stress_MPa']:.2f} MPa")
    print(f"  Bearing Radial Load:    {stress_half['bearing_radial_load_N']:.1f} N")
    print(f"  Bearing Thrust Load:    {stress_half['bearing_thrust_load_N']:.1f} N")
    print()

    # Loss analysis
    losses_full = calc.calculate_losses(I_initial, params.full_load_speed, 50.0)

    print("="*70)
    print("LOSS ANALYSIS AT FULL LOAD:")
    print("="*70)
    print(f"  Copper Loss:            {losses_full['copper_loss']:.2f} W")
    print(f"  Field Loss:             {losses_full['field_loss']:.2f} W")
    print(f"  Iron Loss:              {losses_full['iron_loss']:.2f} W")
    print(f"  Friction Loss:          {losses_full['friction_loss']:.2f} W")
    print(f"  Stray Loss:             {losses_full['stray_loss']:.2f} W")
    print(f"  Total Loss:             {losses_full['total_loss']:.2f} W")
    print()

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

    return calc


if __name__ == "__main__":
    # Run analysis with problem specifications
    params = MotorParameters(
        power_hp=37.5,
        voltage=220.0,
        full_load_speed=535.0,
        armature_resistance=0.086,
        full_load_current=140.0,
        target_braking_current=200.0
    )

    calc = print_analysis_report(params)

    print("\nRunning dynamic simulation...")
    simulator = MultiPhysicsSimulator(calc)
    results = simulator.simulate_rk45((0, 3.0), method='RK45')

    if results['success']:
        print(f"✓ Simulation completed successfully")
        print(f"  Initial speed: {results['speed_rpm'][0]:.1f} RPM")
        print(f"  Final speed: {results['speed_rpm'][-1]:.1f} RPM")
        print(f"  Braking time: {results['time'][-1]:.2f} s")
        print(f"  Final temperature: {results['temperature'][-1]:.1f} °C")
        print(f"  Total energy dissipated: {results['heat'][-1]/1000:.2f} kJ")
    else:
        print(f"✗ Simulation failed: {results['message']}")
