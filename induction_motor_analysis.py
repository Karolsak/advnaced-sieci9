#!/usr/bin/env python3
"""
Advanced Induction Motor Analysis Tool
Solves Example 6.3 and provides comprehensive multi-physics simulation
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy.integrate import odeint, solve_ivp
from scipy.optimize import fsolve
import threading
import time
from dataclasses import dataclass
from typing import Tuple, Dict, List

# ============================================================================
# DATA CLASSES FOR MOTOR PARAMETERS
# ============================================================================

@dataclass
class MotorParameters:
    """Induction motor equivalent circuit parameters"""
    # Ratings
    power_rated: float = 7500  # W
    voltage_rated: float = 380  # V (line-to-line)
    speed_rated: float = 1450  # rpm
    frequency_rated: float = 50  # Hz
    poles: int = 4
    connection: str = "delta"

    # Equivalent circuit parameters (Ohms)
    R1: float = 2.144  # Stator resistance
    R2_prime: float = 1.323  # Rotor resistance referred to stator
    X1: float = 2.891  # Stator leakage reactance
    X2_prime: float = 5.487  # Rotor leakage reactance referred to stator
    Xm: float = 116.3  # Magnetizing reactance

    # Mechanical parameters
    J: float = 0.05  # Moment of inertia (kg·m²)
    B: float = 0.01  # Friction coefficient (N·m·s)

    # Thermal parameters
    thermal_resistance: float = 2.5  # °C/W
    thermal_capacitance: float = 1200  # J/°C
    ambient_temp: float = 25  # °C

    # Economic parameters
    electricity_cost: float = 0.12  # $/kWh
    maintenance_cost_annual: float = 500  # $/year
    initial_cost: float = 2000  # $


@dataclass
class ControlParameters:
    """Control parameters for VSI operation"""
    v_f_ratio: float = 7.6  # V/Hz (380V/50Hz)
    freq_min: float = 5  # Hz
    freq_max: float = 75  # Hz
    control_method: str = "V/f constant"  # V/f, FOC, DTC
    pwm_frequency: float = 5000  # Hz


# ============================================================================
# MOTOR CALCULATIONS - EXAMPLE 6.3 SOLUTION
# ============================================================================

class InductionMotorModel:
    """Complete induction motor equivalent circuit model"""

    def __init__(self, params: MotorParameters):
        self.params = params
        self.history = {
            'time': [],
            'speed': [],
            'torque': [],
            'current': [],
            'temperature': [],
            'power': [],
            'efficiency': [],
            'losses': []
        }

    def calculate_synchronous_speed(self, freq: float) -> float:
        """Calculate synchronous speed in rpm"""
        return 120 * freq / self.params.poles

    def calculate_slip(self, speed_rpm: float, freq: float) -> float:
        """Calculate slip"""
        n_sync = self.calculate_synchronous_speed(freq)
        return (n_sync - speed_rpm) / n_sync

    def calculate_phase_voltage(self, voltage_ll: float) -> float:
        """Calculate phase voltage based on connection type"""
        if self.params.connection.lower() == "delta":
            return voltage_ll
        else:  # Star
            return voltage_ll / np.sqrt(3)

    def calculate_impedance(self, slip: float, freq: float) -> complex:
        """Calculate total motor impedance at given slip and frequency"""
        # Scale reactances with frequency
        freq_ratio = freq / self.params.frequency_rated
        X1 = self.params.X1 * freq_ratio
        X2 = self.params.X2_prime * freq_ratio
        Xm = self.params.Xm * freq_ratio

        # Rotor impedance
        if abs(slip) < 1e-6:
            Z_rotor = 1e10 + 1j * X2  # Very high impedance at zero slip
        else:
            Z_rotor = self.params.R2_prime / slip + 1j * X2

        # Parallel combination of Xm and rotor branch
        Z_parallel = (1j * Xm * Z_rotor) / (1j * Xm + Z_rotor)

        # Total impedance
        Z_total = self.params.R1 + 1j * X1 + Z_parallel

        return Z_total

    def calculate_current_torque(self, voltage: float, freq: float,
                                 slip: float) -> Tuple[float, float]:
        """Calculate stator current (RMS) and developed torque"""
        # Phase voltage
        V_ph = self.calculate_phase_voltage(voltage)

        # Calculate impedance
        Z_total = self.calculate_impedance(slip, freq)

        # Stator current (RMS)
        I1 = abs(V_ph / Z_total)

        # Calculate rotor current and power
        freq_ratio = freq / self.params.frequency_rated
        X1 = self.params.X1 * freq_ratio
        X2 = self.params.X2_prime * freq_ratio
        Xm = self.params.Xm * freq_ratio

        # Thevenin equivalent
        Z_th = (1j * Xm * (self.params.R1 + 1j * X1)) / \
               (self.params.R1 + 1j * (X1 + Xm))
        V_th = V_ph * (1j * Xm) / (self.params.R1 + 1j * (X1 + Xm))

        R_th = abs(Z_th.real)
        X_th = abs(Z_th.imag)

        # Rotor current
        if abs(slip) < 1e-6:
            I2 = 0
        else:
            I2 = abs(V_th) / np.sqrt((R_th + self.params.R2_prime/slip)**2 +
                                     (X_th + X2)**2)

        # Air gap power
        if abs(slip) < 1e-6:
            P_ag = 0
        else:
            P_ag = 3 * I2**2 * self.params.R2_prime / slip

        # Synchronous speed in rad/s
        omega_sync = 2 * np.pi * freq / (self.params.poles / 2)

        # Developed torque
        if abs(omega_sync) < 1e-6:
            T_dev = 0
        else:
            T_dev = P_ag / omega_sync

        return I1, T_dev

    def calculate_starting_values(self, freq: float, voltage: float = None) -> Dict:
        """Calculate starting current and torque (slip = 1)"""
        if voltage is None:
            # V/f control
            voltage = (freq / self.params.frequency_rated) * self.params.voltage_rated

        I_start, T_start = self.calculate_current_torque(voltage, freq, slip=1.0)

        # Line current (for delta connection, line current = sqrt(3) * phase current)
        if self.params.connection.lower() == "delta":
            I_line = np.sqrt(3) * I_start
        else:
            I_line = I_start

        return {
            'frequency': freq,
            'voltage': voltage,
            'current_phase': I_start,
            'current_line': I_line,
            'torque': T_start,
            'slip': 1.0
        }

    def calculate_breakdown_torque(self, freq: float, voltage: float = None) -> float:
        """Calculate maximum (breakdown) torque"""
        if voltage is None:
            voltage = (freq / self.params.frequency_rated) * self.params.voltage_rated

        V_ph = self.calculate_phase_voltage(voltage)

        freq_ratio = freq / self.params.frequency_rated
        X1 = self.params.X1 * freq_ratio
        X2 = self.params.X2_prime * freq_ratio
        Xm = self.params.Xm * freq_ratio

        # Thevenin equivalent
        Z_th = (1j * Xm * (self.params.R1 + 1j * X1)) / \
               (self.params.R1 + 1j * (X1 + Xm))
        V_th = V_ph * (1j * Xm) / (self.params.R1 + 1j * (X1 + Xm))

        R_th = Z_th.real
        X_th = Z_th.imag

        # Synchronous speed
        omega_sync = 2 * np.pi * freq / (self.params.poles / 2)

        # Maximum torque
        T_max = (3 * abs(V_th)**2) / \
                (2 * omega_sync * (R_th + np.sqrt(R_th**2 + (X_th + X2)**2)))

        return T_max

    def solve_example_6_3(self) -> Dict:
        """Complete solution for Example 6.3"""
        results = {}

        # (a) Starting values at rated frequency
        results['rated_freq'] = self.calculate_starting_values(
            self.params.frequency_rated, self.params.voltage_rated)

        # (b) Starting values at minimum frequency
        results['min_freq'] = self.calculate_starting_values(5)

        # Starting values at maximum frequency
        results['max_freq'] = self.calculate_starting_values(75)

        # (c) Breakdown torque as function of frequency
        freq_range = np.linspace(5, 75, 71)
        breakdown_torques = []

        for f in freq_range:
            T_bd = self.calculate_breakdown_torque(f)
            breakdown_torques.append(T_bd)

        results['breakdown_torque_curve'] = {
            'frequency': freq_range,
            'torque': np.array(breakdown_torques)
        }

        return results


# ============================================================================
# DYNAMIC SIMULATION
# ============================================================================

class DynamicSimulator:
    """Dynamic simulation with ODE solvers"""

    def __init__(self, motor_model: InductionMotorModel):
        self.motor = motor_model
        self.params = motor_model.params

    def motor_dynamics_electrical(self, t, x, voltage, freq, load_torque_func):
        """
        State space model for motor dynamics
        States: x = [omega, theta, T_temp]
        omega: rotor speed (rad/s)
        theta: rotor position (rad)
        T_temp: temperature (°C)
        """
        omega = x[0]
        T_temp = x[2]

        # Calculate speed in rpm
        speed_rpm = omega * 60 / (2 * np.pi)

        # Calculate slip
        slip = self.motor.calculate_slip(speed_rpm, freq)

        # Calculate torque
        _, T_em = self.motor.calculate_current_torque(voltage, freq, slip)

        # Load torque
        T_load = load_torque_func(t, omega)

        # Mechanical equation
        d_omega = (T_em - T_load - self.params.B * omega) / self.params.J

        # Position
        d_theta = omega

        # Calculate losses for thermal model
        I1, _ = self.motor.calculate_current_torque(voltage, freq, slip)

        # Copper losses (3-phase)
        P_copper_stator = 3 * I1**2 * self.params.R1

        if abs(slip) > 1e-6:
            I2_squared = (I1**2 * self.params.Xm**2) / \
                        ((self.params.R2_prime/slip)**2 + self.params.X2_prime**2)
            P_copper_rotor = 3 * I2_squared * self.params.R2_prime
        else:
            P_copper_rotor = 0

        # Core losses (approximation)
        P_core = 0.03 * abs(T_em * omega)  # 3% of mechanical power

        # Mechanical losses
        P_mech = self.params.B * omega**2

        # Total losses
        P_loss = P_copper_stator + P_copper_rotor + P_core + P_mech

        # Thermal dynamics
        d_temp = (P_loss - (T_temp - self.params.ambient_temp) /
                  self.params.thermal_resistance) / self.params.thermal_capacitance

        return [d_omega, d_theta, d_temp]

    def simulate_rk45(self, t_span, initial_state, voltage, freq,
                     load_torque_func, t_eval=None):
        """Simulate using RK45 method"""
        sol = solve_ivp(
            fun=lambda t, x: self.motor_dynamics_electrical(
                t, x, voltage, freq, load_torque_func),
            t_span=t_span,
            y0=initial_state,
            method='RK45',
            t_eval=t_eval,
            dense_output=True,
            max_step=0.01
        )
        return sol

    def simulate_euler(self, t_span, initial_state, voltage, freq,
                      load_torque_func, dt=0.001):
        """Simulate using Euler method"""
        t_start, t_end = t_span
        t = np.arange(t_start, t_end, dt)
        n_steps = len(t)

        # Initialize state array
        x = np.zeros((n_steps, len(initial_state)))
        x[0] = initial_state

        # Euler integration
        for i in range(1, n_steps):
            dx = self.motor_dynamics_electrical(
                t[i-1], x[i-1], voltage, freq, load_torque_func)
            x[i] = x[i-1] + dt * np.array(dx)

        return t, x


# ============================================================================
# MULTI-PHYSICS SIMULATION
# ============================================================================

class MultiPhysicsSimulator:
    """Coupled electromagnetic-thermal-mechanical simulation"""

    def __init__(self, motor_model: InductionMotorModel):
        self.motor = motor_model
        self.params = motor_model.params

    def calculate_detailed_losses(self, I1, I2, freq, omega, T_temp):
        """Calculate detailed loss breakdown"""
        losses = {}

        # Copper losses - temperature dependent
        alpha_cu = 0.00393  # Temperature coefficient of copper
        R1_temp = self.params.R1 * (1 + alpha_cu * (T_temp - 25))
        R2_temp = self.params.R2_prime * (1 + alpha_cu * (T_temp - 25))

        losses['copper_stator'] = 3 * I1**2 * R1_temp
        losses['copper_rotor'] = 3 * I2**2 * R2_temp
        losses['copper_total'] = losses['copper_stator'] + losses['copper_rotor']

        # Iron losses (hysteresis + eddy current)
        # Steinmetz equation: P_iron = k_h * f * B^2 + k_e * f^2 * B^2
        # Approximate B from magnetizing current
        V_ph = self.motor.calculate_phase_voltage(self.params.voltage_rated)
        flux_approx = V_ph / (2 * np.pi * freq)

        k_h = 0.001  # Hysteresis coefficient
        k_e = 0.0001  # Eddy current coefficient

        losses['hysteresis'] = k_h * freq * flux_approx**2
        losses['eddy_current'] = k_e * freq**2 * flux_approx**2
        losses['iron_total'] = losses['hysteresis'] + losses['eddy_current']

        # Mechanical losses
        # Friction losses proportional to speed^2
        losses['friction'] = self.params.B * omega**2

        # Windage losses (approximation)
        losses['windage'] = 0.01 * abs(omega)**3
        losses['mechanical_total'] = losses['friction'] + losses['windage']

        # Stray load losses (approximation: 1% of output power)
        P_out = abs(self.motor.calculate_current_torque(
            self.params.voltage_rated, freq,
            self.motor.calculate_slip(omega * 60 / (2*np.pi), freq))[1] * omega)
        losses['stray_load'] = 0.01 * P_out

        # Total losses
        losses['total'] = sum([v for k, v in losses.items()
                              if k not in ['copper_total', 'iron_total', 'mechanical_total']])

        return losses

    def calculate_thermal_distribution(self, losses, T_ambient):
        """Calculate temperature distribution in motor"""
        # Simplified lumped parameter thermal model
        # Three nodes: stator, rotor, frame

        # Thermal resistances (°C/W)
        R_th_stator_frame = 1.5
        R_th_rotor_stator = 2.0
        R_th_frame_ambient = 3.0

        # Thermal capacitances (J/°C)
        C_th_stator = 800
        C_th_rotor = 600
        C_th_frame = 1000

        # Power dissipation at each node
        P_stator = losses['copper_stator'] + losses['iron_total'] * 0.7
        P_rotor = losses['copper_rotor'] + losses['mechanical_total']
        P_frame = losses['iron_total'] * 0.3 + losses['stray_load']

        # Steady-state temperature (simplified)
        T_frame = T_ambient + P_frame * R_th_frame_ambient
        T_stator = T_frame + P_stator * R_th_stator_frame
        T_rotor = T_stator + P_rotor * R_th_rotor_stator

        return {
            'stator': T_stator,
            'rotor': T_rotor,
            'frame': T_frame,
            'max': max(T_stator, T_rotor, T_frame),
            'capacitances': {
                'stator': C_th_stator,
                'rotor': C_th_rotor,
                'frame': C_th_frame
            }
        }

    def calculate_mechanical_stress(self, T_em, omega, alpha_accel):
        """Calculate shaft torque transients and bearing loads"""
        stress = {}

        # Shaft torque
        stress['shaft_torque'] = T_em
        stress['shaft_stress'] = T_em / (np.pi * 0.03**3 / 16)  # Assume 30mm diameter

        # Bearing loads
        # Radial load from electromagnetic forces
        stress['bearing_radial'] = abs(T_em) / 0.1  # Assume 100mm bearing spacing

        # Axial load (approximation)
        stress['bearing_axial'] = 0.1 * stress['bearing_radial']

        # Dynamic load from acceleration
        stress['dynamic_load'] = self.params.J * alpha_accel / 0.05  # Assume 50mm radius

        # Total bearing load
        stress['bearing_total'] = np.sqrt(stress['bearing_radial']**2 +
                                         stress['bearing_axial']**2 +
                                         stress['dynamic_load']**2)

        return stress

    def calculate_derating(self, T_max, altitude, voltage_variation):
        """Calculate derating factors"""
        derating = {}

        # Temperature derating
        if T_max > 155:  # Class F insulation
            derating['temperature'] = 0.7
        elif T_max > 130:
            derating['temperature'] = 0.85
        elif T_max > 105:
            derating['temperature'] = 0.95
        else:
            derating['temperature'] = 1.0

        # Altitude derating (per 1000m above 1000m)
        if altitude > 1000:
            derating['altitude'] = 1.0 - 0.01 * ((altitude - 1000) / 100)
        else:
            derating['altitude'] = 1.0

        # Voltage variation derating
        if abs(voltage_variation) > 0.1:  # >10% variation
            derating['voltage'] = 0.9
        else:
            derating['voltage'] = 1.0

        # Overall derating
        derating['overall'] = (derating['temperature'] *
                              derating['altitude'] *
                              derating['voltage'])

        return derating


# ============================================================================
# ADVANCED CONTROL METHODS
# ============================================================================

class AdvancedController:
    """Advanced motor control methods"""

    def __init__(self, motor_model: InductionMotorModel):
        self.motor = motor_model
        self.params = motor_model.params

    def vf_control(self, freq, boost=0):
        """V/f control with boost"""
        v_f_ratio = self.params.voltage_rated / self.params.frequency_rated
        voltage = v_f_ratio * freq + boost
        return min(voltage, self.params.voltage_rated * 1.1)  # Limit to 110%

    def field_oriented_control(self, omega_ref, omega_actual, T_load):
        """Simplified Field Oriented Control (FOC)"""
        # Speed error
        error = omega_ref - omega_actual

        # PI controller for speed
        Kp = 5.0
        Ki = 2.0

        # Torque command
        T_cmd = Kp * error + Ki * np.trapz([error], dx=0.01)

        # Flux command (constant for base speed)
        flux_cmd = self.params.voltage_rated / (2 * np.pi * self.params.frequency_rated)

        # Current commands (id, iq)
        Lm = self.params.Xm / (2 * np.pi * self.params.frequency_rated)
        id_cmd = flux_cmd / Lm

        # iq for torque
        K_t = 1.5 * self.params.poles / 2 * Lm
        iq_cmd = T_cmd / (K_t * id_cmd)

        return {
            'torque_cmd': T_cmd,
            'flux_cmd': flux_cmd,
            'id': id_cmd,
            'iq': iq_cmd,
            'current_magnitude': np.sqrt(id_cmd**2 + iq_cmd**2)
        }

    def direct_torque_control(self, T_ref, flux_ref, T_actual, flux_actual):
        """Simplified Direct Torque Control (DTC)"""
        # Hysteresis comparators
        T_hyst = 0.5  # Nm
        flux_hyst = 0.01  # Wb

        # Torque error
        T_error = T_ref - T_actual

        # Flux error
        flux_error = flux_ref - flux_actual

        # Select voltage vector based on errors
        if T_error > T_hyst:
            if flux_error > flux_hyst:
                sector = 1  # Increase both
            else:
                sector = 2  # Increase torque, decrease flux
        else:
            if flux_error > flux_hyst:
                sector = 3  # Decrease torque, increase flux
            else:
                sector = 0  # Zero vector

        return {
            'sector': sector,
            'torque_error': T_error,
            'flux_error': flux_error
        }

    def soft_start(self, t, t_ramp=5.0):
        """Soft start profile"""
        if t < t_ramp:
            return (t / t_ramp) * self.params.frequency_rated
        else:
            return self.params.frequency_rated

    def energy_optimization(self, load_torque, speed):
        """Optimize flux level for minimum losses at given load"""
        # Simplified loss minimization
        # Reduce flux at light load
        rated_torque = self.params.power_rated / \
                      (2 * np.pi * self.params.speed_rated / 60)

        load_ratio = abs(load_torque) / rated_torque

        if load_ratio < 0.5:
            flux_ratio = 0.7 + 0.3 * load_ratio / 0.5
        else:
            flux_ratio = 1.0

        return flux_ratio


# ============================================================================
# ECONOMIC ANALYSIS
# ============================================================================

class EconomicAnalyzer:
    """Economic analysis for motor operation"""

    def __init__(self, motor_model: InductionMotorModel):
        self.motor = motor_model
        self.params = motor_model.params

    def calculate_energy_consumption(self, operating_hours_per_year,
                                    avg_load_factor, efficiency):
        """Calculate annual energy consumption"""
        P_out_avg = self.params.power_rated * avg_load_factor
        P_in_avg = P_out_avg / efficiency

        energy_kwh = P_in_avg * operating_hours_per_year / 1000

        return {
            'energy_kwh': energy_kwh,
            'cost_annual': energy_kwh * self.params.electricity_cost
        }

    def calculate_lifecycle_cost(self, lifetime_years, operating_hours_per_year,
                                avg_load_factor, efficiency, discount_rate=0.05):
        """Calculate lifecycle cost (LCC)"""
        # Initial cost
        lcc = self.params.initial_cost

        # Annual costs
        energy = self.calculate_energy_consumption(
            operating_hours_per_year, avg_load_factor, efficiency)
        annual_cost = energy['cost_annual'] + self.params.maintenance_cost_annual

        # Present value of annual costs
        pv_annual = 0
        for year in range(1, lifetime_years + 1):
            pv_annual += annual_cost / ((1 + discount_rate) ** year)

        lcc += pv_annual

        return {
            'initial_cost': self.params.initial_cost,
            'annual_energy_cost': energy['cost_annual'],
            'annual_maintenance_cost': self.params.maintenance_cost_annual,
            'present_value_annual_costs': pv_annual,
            'total_lifecycle_cost': lcc
        }

    def calculate_efficiency(self, P_out, losses):
        """Calculate efficiency"""
        P_in = P_out + losses
        if P_in > 0:
            return P_out / P_in
        else:
            return 0

    def payback_analysis(self, old_motor_efficiency, new_motor_efficiency,
                        new_motor_cost, operating_hours_per_year, avg_load_factor):
        """Simple payback period for motor replacement"""
        P_out_avg = self.params.power_rated * avg_load_factor

        # Old motor energy cost
        P_in_old = P_out_avg / old_motor_efficiency
        energy_old = P_in_old * operating_hours_per_year / 1000
        cost_old = energy_old * self.params.electricity_cost

        # New motor energy cost
        P_in_new = P_out_avg / new_motor_efficiency
        energy_new = P_in_new * operating_hours_per_year / 1000
        cost_new = energy_new * self.params.electricity_cost

        # Annual savings
        savings_annual = cost_old - cost_new

        # Payback period
        if savings_annual > 0:
            payback_years = new_motor_cost / savings_annual
        else:
            payback_years = float('inf')

        return {
            'old_energy_cost': cost_old,
            'new_energy_cost': cost_new,
            'annual_savings': savings_annual,
            'payback_years': payback_years,
            'investment': new_motor_cost
        }


# ============================================================================
# MAIN GUI APPLICATION
# ============================================================================

class InductionMotorGUI:
    """Main Tkinter GUI application"""

    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Induction Motor Analysis - Example 6.3")
        self.root.geometry("1400x900")

        # Initialize models
        self.motor_params = MotorParameters()
        self.control_params = ControlParameters()
        self.motor_model = InductionMotorModel(self.motor_params)
        self.dynamic_sim = DynamicSimulator(self.motor_model)
        self.multiphysics_sim = MultiPhysicsSimulator(self.motor_model)
        self.controller = AdvancedController(self.motor_model)
        self.economic = EconomicAnalyzer(self.motor_model)

        # Simulation state
        self.simulation_running = False
        self.simulation_thread = None

        # Setup GUI
        self.setup_gui()

        # Bind resize event for auto-scaling
        self.root.bind('<Configure>', self.on_resize)

    def setup_gui(self):
        """Setup main GUI layout"""
        # Main menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Parameters", command=self.load_parameters)
        file_menu.add_command(label="Save Results", command=self.save_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Create tabs
        self.create_example63_tab()
        self.create_parameters_tab()
        self.create_control_tab()
        self.create_dynamic_simulation_tab()
        self.create_multiphysics_tab()
        self.create_economic_tab()
        self.create_results_tab()

    def create_example63_tab(self):
        """Tab for Example 6.3 solution"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Example 6.3 Solution")

        # Control frame
        control_frame = ttk.LabelFrame(tab, text="Controls", padding=10)
        control_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(control_frame, text="Solve Example 6.3",
                  command=self.solve_example_63).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Clear Results",
                  command=self.clear_example_results).pack(side='left', padx=5)

        # Results text area
        results_frame = ttk.LabelFrame(tab, text="Results", padding=10)
        results_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.example_results_text = scrolledtext.ScrolledText(
            results_frame, wrap=tk.WORD, height=15, font=('Courier', 10))
        self.example_results_text.pack(fill='both', expand=True)

        # Plot frame
        plot_frame = ttk.LabelFrame(tab, text="Breakdown Torque vs Frequency", padding=10)
        plot_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.example_fig = Figure(figsize=(10, 4), dpi=100)
        self.example_ax = self.example_fig.add_subplot(111)
        self.example_canvas = FigureCanvasTkAgg(self.example_fig, plot_frame)
        self.example_canvas.get_tk_widget().pack(fill='both', expand=True)

    def create_parameters_tab(self):
        """Tab for input parameters"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Motor Parameters")

        # Create scrollable frame
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Ratings
        ratings_frame = ttk.LabelFrame(scrollable_frame, text="Ratings", padding=10)
        ratings_frame.pack(fill='x', padx=10, pady=5)

        self.param_vars = {}
        params_layout = [
            ("Power (W):", "power_rated"),
            ("Voltage (V):", "voltage_rated"),
            ("Speed (rpm):", "speed_rated"),
            ("Frequency (Hz):", "frequency_rated"),
            ("Poles:", "poles")
        ]

        for i, (label, param) in enumerate(params_layout):
            ttk.Label(ratings_frame, text=label).grid(row=i, column=0, sticky='w', pady=2)
            var = tk.DoubleVar(value=getattr(self.motor_params, param))
            self.param_vars[param] = var
            ttk.Entry(ratings_frame, textvariable=var, width=15).grid(
                row=i, column=1, padx=5, pady=2)

        # Circuit parameters
        circuit_frame = ttk.LabelFrame(scrollable_frame,
                                      text="Equivalent Circuit Parameters (Ω)",
                                      padding=10)
        circuit_frame.pack(fill='x', padx=10, pady=5)

        circuit_params = [
            ("R1 (Stator Resistance):", "R1"),
            ("R2' (Rotor Resistance):", "R2_prime"),
            ("X1 (Stator Reactance):", "X1"),
            ("X2' (Rotor Reactance):", "X2_prime"),
            ("Xm (Magnetizing Reactance):", "Xm")
        ]

        for i, (label, param) in enumerate(circuit_params):
            ttk.Label(circuit_frame, text=label).grid(row=i, column=0, sticky='w', pady=2)
            var = tk.DoubleVar(value=getattr(self.motor_params, param))
            self.param_vars[param] = var
            ttk.Entry(circuit_frame, textvariable=var, width=15).grid(
                row=i, column=1, padx=5, pady=2)

        # Update button
        ttk.Button(scrollable_frame, text="Update Parameters",
                  command=self.update_parameters).pack(pady=10)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_control_tab(self):
        """Tab for control settings"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Control")

        # Control method selection
        method_frame = ttk.LabelFrame(tab, text="Control Method", padding=10)
        method_frame.pack(fill='x', padx=10, pady=5)

        self.control_method_var = tk.StringVar(value="V/f constant")
        methods = ["V/f constant", "Field Oriented Control (FOC)",
                  "Direct Torque Control (DTC)", "Energy Optimization"]

        for method in methods:
            ttk.Radiobutton(method_frame, text=method,
                           variable=self.control_method_var,
                           value=method).pack(anchor='w')

        # Frequency control
        freq_frame = ttk.LabelFrame(tab, text="Frequency Control", padding=10)
        freq_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(freq_frame, text="Frequency (Hz):").grid(row=0, column=0, sticky='w')
        self.freq_var = tk.DoubleVar(value=50)
        self.freq_slider = ttk.Scale(freq_frame, from_=5, to=75,
                                     variable=self.freq_var, orient='horizontal',
                                     length=400, command=self.on_freq_change)
        self.freq_slider.grid(row=0, column=1, padx=5)
        self.freq_label = ttk.Label(freq_frame, text="50.0 Hz")
        self.freq_label.grid(row=0, column=2)

        # Voltage control
        ttk.Label(freq_frame, text="Voltage (V):").grid(row=1, column=0, sticky='w', pady=5)
        self.voltage_var = tk.DoubleVar(value=380)
        self.voltage_slider = ttk.Scale(freq_frame, from_=0, to=450,
                                       variable=self.voltage_var, orient='horizontal',
                                       length=400, command=self.on_voltage_change)
        self.voltage_slider.grid(row=1, column=1, padx=5, pady=5)
        self.voltage_label = ttk.Label(freq_frame, text="380.0 V")
        self.voltage_label.grid(row=1, column=2, pady=5)

        # Load torque control
        ttk.Label(freq_frame, text="Load Torque (Nm):").grid(row=2, column=0, sticky='w')
        self.torque_var = tk.DoubleVar(value=30)
        self.torque_slider = ttk.Scale(freq_frame, from_=0, to=100,
                                       variable=self.torque_var, orient='horizontal',
                                       length=400, command=self.on_torque_change)
        self.torque_slider.grid(row=2, column=1, padx=5)
        self.torque_label = ttk.Label(freq_frame, text="30.0 Nm")
        self.torque_label.grid(row=2, column=2)

        # Real-time calculations
        calc_frame = ttk.LabelFrame(tab, text="Real-time Calculations", padding=10)
        calc_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.control_calc_text = scrolledtext.ScrolledText(
            calc_frame, wrap=tk.WORD, height=15, font=('Courier', 10))
        self.control_calc_text.pack(fill='both', expand=True)

        ttk.Button(calc_frame, text="Calculate",
                  command=self.calculate_control_values).pack(pady=5)

    def create_dynamic_simulation_tab(self):
        """Tab for dynamic simulation"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Dynamic Simulation")

        # Control panel
        control_frame = ttk.LabelFrame(tab, text="Simulation Controls", padding=10)
        control_frame.pack(fill='x', padx=10, pady=5)

        # Solver selection
        ttk.Label(control_frame, text="Solver:").grid(row=0, column=0, sticky='w')
        self.solver_var = tk.StringVar(value="RK45")
        ttk.Radiobutton(control_frame, text="RK45", variable=self.solver_var,
                       value="RK45").grid(row=0, column=1, sticky='w')
        ttk.Radiobutton(control_frame, text="Euler", variable=self.solver_var,
                       value="Euler").grid(row=0, column=2, sticky='w')

        # Time span
        ttk.Label(control_frame, text="Simulation Time (s):").grid(
            row=1, column=0, sticky='w', pady=5)
        self.sim_time_var = tk.DoubleVar(value=5.0)
        ttk.Entry(control_frame, textvariable=self.sim_time_var, width=10).grid(
            row=1, column=1, pady=5)

        # Buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=10)

        self.start_button = ttk.Button(button_frame, text="Start",
                                       command=self.start_simulation)
        self.start_button.pack(side='left', padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop",
                                      command=self.stop_simulation, state='disabled')
        self.stop_button.pack(side='left', padx=5)

        ttk.Button(button_frame, text="Reset",
                  command=self.reset_simulation).pack(side='left', padx=5)

        # Progress bar
        self.sim_progress = ttk.Progressbar(control_frame, mode='indeterminate')
        self.sim_progress.grid(row=3, column=0, columnspan=3, sticky='ew', pady=5)

        # Plots
        plot_frame = ttk.Frame(tab)
        plot_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.sim_fig = Figure(figsize=(12, 8), dpi=100)

        self.sim_ax1 = self.sim_fig.add_subplot(221)
        self.sim_ax1.set_title('Speed vs Time')
        self.sim_ax1.set_xlabel('Time (s)')
        self.sim_ax1.set_ylabel('Speed (rpm)')
        self.sim_ax1.grid(True)

        self.sim_ax2 = self.sim_fig.add_subplot(222)
        self.sim_ax2.set_title('Torque vs Time')
        self.sim_ax2.set_xlabel('Time (s)')
        self.sim_ax2.set_ylabel('Torque (Nm)')
        self.sim_ax2.grid(True)

        self.sim_ax3 = self.sim_fig.add_subplot(223)
        self.sim_ax3.set_title('Current vs Time')
        self.sim_ax3.set_xlabel('Time (s)')
        self.sim_ax3.set_ylabel('Current (A)')
        self.sim_ax3.grid(True)

        self.sim_ax4 = self.sim_fig.add_subplot(224)
        self.sim_ax4.set_title('Temperature vs Time')
        self.sim_ax4.set_xlabel('Time (s)')
        self.sim_ax4.set_ylabel('Temperature (°C)')
        self.sim_ax4.grid(True)

        self.sim_fig.tight_layout()

        self.sim_canvas = FigureCanvasTkAgg(self.sim_fig, plot_frame)
        self.sim_canvas.get_tk_widget().pack(fill='both', expand=True)

    def create_multiphysics_tab(self):
        """Tab for multi-physics simulation"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Multi-Physics Analysis")

        # Control frame
        control_frame = ttk.LabelFrame(tab, text="Analysis Controls", padding=10)
        control_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(control_frame, text="Run Multi-Physics Analysis",
                  command=self.run_multiphysics).pack(side='left', padx=5)

        # Operating point
        op_frame = ttk.LabelFrame(control_frame, text="Operating Point", padding=5)
        op_frame.pack(side='left', padx=10)

        ttk.Label(op_frame, text="Speed:").grid(row=0, column=0)
        self.mp_speed_var = tk.DoubleVar(value=1450)
        ttk.Entry(op_frame, textvariable=self.mp_speed_var, width=10).grid(row=0, column=1)
        ttk.Label(op_frame, text="rpm").grid(row=0, column=2)

        # Results notebook
        results_notebook = ttk.Notebook(tab)
        results_notebook.pack(fill='both', expand=True, padx=10, pady=5)

        # Losses tab
        losses_frame = ttk.Frame(results_notebook)
        results_notebook.add(losses_frame, text="Loss Breakdown")

        self.losses_text = scrolledtext.ScrolledText(
            losses_frame, wrap=tk.WORD, font=('Courier', 10))
        self.losses_text.pack(fill='both', expand=True)

        # Thermal tab
        thermal_frame = ttk.Frame(results_notebook)
        results_notebook.add(thermal_frame, text="Thermal Analysis")

        self.thermal_fig = Figure(figsize=(10, 6), dpi=100)
        self.thermal_ax = self.thermal_fig.add_subplot(111)
        self.thermal_canvas = FigureCanvasTkAgg(self.thermal_fig, thermal_frame)
        self.thermal_canvas.get_tk_widget().pack(fill='both', expand=True)

        # Mechanical stress tab
        stress_frame = ttk.Frame(results_notebook)
        results_notebook.add(stress_frame, text="Mechanical Stress")

        self.stress_text = scrolledtext.ScrolledText(
            stress_frame, wrap=tk.WORD, font=('Courier', 10))
        self.stress_text.pack(fill='both', expand=True)

        # Derating tab
        derating_frame = ttk.Frame(results_notebook)
        results_notebook.add(derating_frame, text="Derating Analysis")

        derate_input_frame = ttk.LabelFrame(derating_frame,
                                           text="Environmental Conditions",
                                           padding=10)
        derate_input_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(derate_input_frame, text="Altitude (m):").grid(row=0, column=0, sticky='w')
        self.altitude_var = tk.DoubleVar(value=0)
        ttk.Entry(derate_input_frame, textvariable=self.altitude_var, width=10).grid(
            row=0, column=1)

        ttk.Label(derate_input_frame, text="Voltage Variation (%):").grid(
            row=1, column=0, sticky='w', pady=5)
        self.voltage_variation_var = tk.DoubleVar(value=0)
        ttk.Entry(derate_input_frame, textvariable=self.voltage_variation_var,
                 width=10).grid(row=1, column=1, pady=5)

        self.derating_text = scrolledtext.ScrolledText(
            derating_frame, wrap=tk.WORD, font=('Courier', 10))
        self.derating_text.pack(fill='both', expand=True, padx=10, pady=5)

    def create_economic_tab(self):
        """Tab for economic analysis"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Economic Analysis")

        # Input frame
        input_frame = ttk.LabelFrame(tab, text="Operating Conditions", padding=10)
        input_frame.pack(fill='x', padx=10, pady=5)

        # Operating hours
        ttk.Label(input_frame, text="Operating Hours/Year:").grid(
            row=0, column=0, sticky='w', pady=2)
        self.op_hours_var = tk.DoubleVar(value=4000)
        ttk.Entry(input_frame, textvariable=self.op_hours_var, width=15).grid(
            row=0, column=1, padx=5, pady=2)

        # Load factor
        ttk.Label(input_frame, text="Average Load Factor:").grid(
            row=1, column=0, sticky='w', pady=2)
        self.load_factor_var = tk.DoubleVar(value=0.75)
        ttk.Entry(input_frame, textvariable=self.load_factor_var, width=15).grid(
            row=1, column=1, padx=5, pady=2)

        # Efficiency
        ttk.Label(input_frame, text="Efficiency:").grid(
            row=2, column=0, sticky='w', pady=2)
        self.efficiency_var = tk.DoubleVar(value=0.90)
        ttk.Entry(input_frame, textvariable=self.efficiency_var, width=15).grid(
            row=2, column=1, padx=5, pady=2)

        # Lifetime
        ttk.Label(input_frame, text="Lifetime (years):").grid(
            row=3, column=0, sticky='w', pady=2)
        self.lifetime_var = tk.DoubleVar(value=15)
        ttk.Entry(input_frame, textvariable=self.lifetime_var, width=15).grid(
            row=3, column=1, padx=5, pady=2)

        # Electricity cost
        ttk.Label(input_frame, text="Electricity Cost ($/kWh):").grid(
            row=4, column=0, sticky='w', pady=2)
        self.elec_cost_var = tk.DoubleVar(value=0.12)
        ttk.Entry(input_frame, textvariable=self.elec_cost_var, width=15).grid(
            row=4, column=1, padx=5, pady=2)

        # Calculate button
        ttk.Button(input_frame, text="Calculate Economics",
                  command=self.calculate_economics).grid(
            row=5, column=0, columnspan=2, pady=10)

        # Results notebook
        results_notebook = ttk.Notebook(tab)
        results_notebook.pack(fill='both', expand=True, padx=10, pady=5)

        # Energy consumption tab
        energy_frame = ttk.Frame(results_notebook)
        results_notebook.add(energy_frame, text="Energy Consumption")

        self.energy_text = scrolledtext.ScrolledText(
            energy_frame, wrap=tk.WORD, font=('Courier', 10))
        self.energy_text.pack(fill='both', expand=True)

        # Lifecycle cost tab
        lcc_frame = ttk.Frame(results_notebook)
        results_notebook.add(lcc_frame, text="Lifecycle Cost")

        self.lcc_text = scrolledtext.ScrolledText(
            lcc_frame, wrap=tk.WORD, font=('Courier', 10))
        self.lcc_text.pack(fill='both', expand=True)

        # Payback analysis tab
        payback_frame = ttk.Frame(results_notebook)
        results_notebook.add(payback_frame, text="Payback Analysis")

        payback_input_frame = ttk.LabelFrame(payback_frame,
                                            text="Motor Comparison",
                                            padding=10)
        payback_input_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(payback_input_frame, text="Old Motor Efficiency:").grid(
            row=0, column=0, sticky='w')
        self.old_eff_var = tk.DoubleVar(value=0.85)
        ttk.Entry(payback_input_frame, textvariable=self.old_eff_var, width=10).grid(
            row=0, column=1)

        ttk.Label(payback_input_frame, text="New Motor Efficiency:").grid(
            row=1, column=0, sticky='w', pady=5)
        self.new_eff_var = tk.DoubleVar(value=0.93)
        ttk.Entry(payback_input_frame, textvariable=self.new_eff_var, width=10).grid(
            row=1, column=1, pady=5)

        ttk.Label(payback_input_frame, text="New Motor Cost ($):").grid(
            row=2, column=0, sticky='w')
        self.new_cost_var = tk.DoubleVar(value=3000)
        ttk.Entry(payback_input_frame, textvariable=self.new_cost_var, width=10).grid(
            row=2, column=1)

        ttk.Button(payback_input_frame, text="Calculate Payback",
                  command=self.calculate_payback).grid(
            row=3, column=0, columnspan=2, pady=10)

        self.payback_text = scrolledtext.ScrolledText(
            payback_frame, wrap=tk.WORD, font=('Courier', 10))
        self.payback_text.pack(fill='both', expand=True, padx=10, pady=5)

    def create_results_tab(self):
        """Tab for comprehensive results visualization"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Results Summary")

        # Create text widget for summary
        self.summary_text = scrolledtext.ScrolledText(
            tab, wrap=tk.WORD, font=('Courier', 10))
        self.summary_text.pack(fill='both', expand=True, padx=10, pady=10)

        # Export button
        ttk.Button(tab, text="Export All Results",
                  command=self.export_results).pack(pady=5)

    # ========================================================================
    # CALLBACK FUNCTIONS
    # ========================================================================

    def on_freq_change(self, value):
        """Update frequency label"""
        self.freq_label.config(text=f"{float(value):.1f} Hz")

    def on_voltage_change(self, value):
        """Update voltage label"""
        self.voltage_label.config(text=f"{float(value):.1f} V")

    def on_torque_change(self, value):
        """Update torque label"""
        self.torque_label.config(text=f"{float(value):.1f} Nm")

    def on_resize(self, event):
        """Handle window resize for auto-scaling"""
        # Update canvas sizes if needed
        pass

    def solve_example_63(self):
        """Solve Example 6.3"""
        try:
            # Update motor model with current parameters
            self.update_motor_model()

            # Solve
            results = self.motor_model.solve_example_6_3()

            # Display results
            self.example_results_text.delete('1.0', tk.END)

            output = "="*70 + "\n"
            output += "SOLUTION TO EXAMPLE 6.3\n"
            output += "="*70 + "\n\n"

            output += "3-Phase Cage Induction Motor Analysis\n"
            output += f"Rated Power: {self.motor_params.power_rated/1000:.1f} kW\n"
            output += f"Rated Voltage: {self.motor_params.voltage_rated} V (line-to-line)\n"
            output += f"Rated Speed: {self.motor_params.speed_rated} rpm\n"
            output += f"Rated Frequency: {self.motor_params.frequency_rated} Hz\n"
            output += f"Connection: {self.motor_params.connection.upper()}\n\n"

            output += "Equivalent Circuit Parameters:\n"
            output += f"  R1 = {self.motor_params.R1:.3f} Ω\n"
            output += f"  R2' = {self.motor_params.R2_prime:.3f} Ω\n"
            output += f"  X1 = {self.motor_params.X1:.3f} Ω\n"
            output += f"  X2' = {self.motor_params.X2_prime:.3f} Ω\n"
            output += f"  Xm = {self.motor_params.Xm:.3f} Ω\n\n"

            output += "="*70 + "\n"
            output += "(a) STARTING VALUES AT RATED FREQUENCY\n"
            output += "="*70 + "\n"
            rated = results['rated_freq']
            output += f"Frequency: {rated['frequency']:.1f} Hz\n"
            output += f"Voltage: {rated['voltage']:.1f} V (line-to-line)\n"
            output += f"Slip: {rated['slip']:.3f}\n"
            output += f"Starting Current (phase): {rated['current_phase']:.2f} A (RMS)\n"
            output += f"Starting Current (line): {rated['current_line']:.2f} A (RMS)\n"
            output += f"Starting Torque: {rated['torque']:.2f} Nm\n\n"

            output += "="*70 + "\n"
            output += "(b) STARTING VALUES AT MINIMUM AND MAXIMUM FREQUENCY\n"
            output += "="*70 + "\n"

            output += "\nMinimum Frequency (5 Hz):\n"
            min_f = results['min_freq']
            output += f"Frequency: {min_f['frequency']:.1f} Hz\n"
            output += f"Voltage: {min_f['voltage']:.1f} V (V/f control)\n"
            output += f"Starting Current (phase): {min_f['current_phase']:.2f} A (RMS)\n"
            output += f"Starting Current (line): {min_f['current_line']:.2f} A (RMS)\n"
            output += f"Starting Torque: {min_f['torque']:.2f} Nm\n\n"

            output += "Maximum Frequency (75 Hz):\n"
            max_f = results['max_freq']
            output += f"Frequency: {max_f['frequency']:.1f} Hz\n"
            output += f"Voltage: {max_f['voltage']:.1f} V (V/f control)\n"
            output += f"Starting Current (phase): {max_f['current_phase']:.2f} A (RMS)\n"
            output += f"Starting Current (line): {max_f['current_line']:.2f} A (RMS)\n"
            output += f"Starting Torque: {max_f['torque']:.2f} Nm\n\n"

            output += "="*70 + "\n"
            output += "(c) BREAKDOWN TORQUE VS FREQUENCY\n"
            output += "="*70 + "\n"
            output += "See plot below for breakdown torque curve\n\n"

            bd_curve = results['breakdown_torque_curve']
            output += "Sample Values:\n"
            for i in range(0, len(bd_curve['frequency']), 10):
                f = bd_curve['frequency'][i]
                T = bd_curve['torque'][i]
                output += f"  f = {f:5.1f} Hz  =>  T_breakdown = {T:7.2f} Nm\n"

            self.example_results_text.insert('1.0', output)

            # Plot breakdown torque curve
            self.example_ax.clear()
            self.example_ax.plot(bd_curve['frequency'], bd_curve['torque'],
                                'b-', linewidth=2, label='Breakdown Torque')
            self.example_ax.axhline(y=rated['torque'], color='r', linestyle='--',
                                   label=f"Starting Torque @ {self.motor_params.frequency_rated} Hz")
            self.example_ax.set_xlabel('Frequency (Hz)', fontsize=12)
            self.example_ax.set_ylabel('Torque (Nm)', fontsize=12)
            self.example_ax.set_title('Breakdown Torque vs Frequency (V/f = constant)',
                                     fontsize=14, fontweight='bold')
            self.example_ax.grid(True, alpha=0.3)
            self.example_ax.legend()
            self.example_fig.tight_layout()
            self.example_canvas.draw()

            messagebox.showinfo("Success", "Example 6.3 solved successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Error solving Example 6.3:\n{str(e)}")

    def clear_example_results(self):
        """Clear example results"""
        self.example_results_text.delete('1.0', tk.END)
        self.example_ax.clear()
        self.example_canvas.draw()

    def update_parameters(self):
        """Update motor parameters from GUI"""
        try:
            for param, var in self.param_vars.items():
                setattr(self.motor_params, param, var.get())

            # Recreate motor model
            self.motor_model = InductionMotorModel(self.motor_params)
            self.dynamic_sim = DynamicSimulator(self.motor_model)
            self.multiphysics_sim = MultiPhysicsSimulator(self.motor_model)
            self.controller = AdvancedController(self.motor_model)
            self.economic = EconomicAnalyzer(self.motor_model)

            messagebox.showinfo("Success", "Parameters updated successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Error updating parameters:\n{str(e)}")

    def update_motor_model(self):
        """Silently update motor model from current GUI values"""
        for param, var in self.param_vars.items():
            if hasattr(self.motor_params, param):
                setattr(self.motor_params, param, var.get())

    def calculate_control_values(self):
        """Calculate values for current control settings"""
        try:
            freq = self.freq_var.get()
            voltage = self.voltage_var.get()
            load_torque = self.torque_var.get()

            # Calculate at different speeds
            speeds = np.linspace(0, 1.1 * self.motor_model.calculate_synchronous_speed(freq), 50)

            self.control_calc_text.delete('1.0', tk.END)

            output = "="*70 + "\n"
            output += "CONTROL CALCULATIONS\n"
            output += "="*70 + "\n\n"
            output += f"Control Method: {self.control_method_var.get()}\n"
            output += f"Frequency: {freq:.1f} Hz\n"
            output += f"Voltage: {voltage:.1f} V\n"
            output += f"Load Torque: {load_torque:.1f} Nm\n\n"

            # Synchronous speed
            n_sync = self.motor_model.calculate_synchronous_speed(freq)
            output += f"Synchronous Speed: {n_sync:.1f} rpm\n\n"

            # Starting values
            starting = self.motor_model.calculate_starting_values(freq, voltage)
            output += "Starting Condition (s = 1.0):\n"
            output += f"  Current (line): {starting['current_line']:.2f} A\n"
            output += f"  Torque: {starting['torque']:.2f} Nm\n\n"

            # Breakdown torque
            T_bd = self.motor_model.calculate_breakdown_torque(freq, voltage)
            output += f"Breakdown Torque: {T_bd:.2f} Nm\n\n"

            # Sample operating points
            output += "Sample Operating Points:\n"
            output += f"{'Speed (rpm)':>12} {'Slip':>8} {'Current (A)':>12} {'Torque (Nm)':>12}\n"
            output += "-"*50 + "\n"

            for speed in speeds[::5]:
                slip = self.motor_model.calculate_slip(speed, freq)
                if 0 <= slip <= 1:
                    I, T = self.motor_model.calculate_current_torque(voltage, freq, slip)
                    if self.motor_params.connection.lower() == "delta":
                        I_line = np.sqrt(3) * I
                    else:
                        I_line = I
                    output += f"{speed:12.1f} {slip:8.4f} {I_line:12.2f} {T:12.2f}\n"

            self.control_calc_text.insert('1.0', output)

        except Exception as e:
            messagebox.showerror("Error", f"Error in calculations:\n{str(e)}")

    def start_simulation(self):
        """Start dynamic simulation"""
        if self.simulation_running:
            messagebox.showwarning("Warning", "Simulation already running!")
            return

        try:
            self.simulation_running = True
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self.sim_progress.start()

            # Run simulation in thread
            self.simulation_thread = threading.Thread(target=self.run_simulation)
            self.simulation_thread.daemon = True
            self.simulation_thread.start()

        except Exception as e:
            self.simulation_running = False
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.sim_progress.stop()
            messagebox.showerror("Error", f"Error starting simulation:\n{str(e)}")

    def stop_simulation(self):
        """Stop simulation"""
        self.simulation_running = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.sim_progress.stop()

    def reset_simulation(self):
        """Reset simulation"""
        self.stop_simulation()

        # Clear plots
        for ax in [self.sim_ax1, self.sim_ax2, self.sim_ax3, self.sim_ax4]:
            ax.clear()

        self.sim_ax1.set_title('Speed vs Time')
        self.sim_ax1.set_xlabel('Time (s)')
        self.sim_ax1.set_ylabel('Speed (rpm)')
        self.sim_ax1.grid(True)

        self.sim_ax2.set_title('Torque vs Time')
        self.sim_ax2.set_xlabel('Time (s)')
        self.sim_ax2.set_ylabel('Torque (Nm)')
        self.sim_ax2.grid(True)

        self.sim_ax3.set_title('Current vs Time')
        self.sim_ax3.set_xlabel('Time (s)')
        self.sim_ax3.set_ylabel('Current (A)')
        self.sim_ax3.grid(True)

        self.sim_ax4.set_title('Temperature vs Time')
        self.sim_ax4.set_xlabel('Time (s)')
        self.sim_ax4.set_ylabel('Temperature (°C)')
        self.sim_ax4.grid(True)

        self.sim_fig.tight_layout()
        self.sim_canvas.draw()

    def run_simulation(self):
        """Run dynamic simulation (called in thread)"""
        try:
            # Get parameters
            sim_time = self.sim_time_var.get()
            freq = self.freq_var.get()
            voltage = self.voltage_var.get()
            load_torque = self.torque_var.get()
            solver = self.solver_var.get()

            # Initial state: [omega, theta, T_temp]
            initial_state = [0, 0, self.motor_params.ambient_temp]

            # Load torque function
            def load_torque_func(t, omega):
                # Constant load torque
                return load_torque

            # Run simulation
            if solver == "RK45":
                t_eval = np.linspace(0, sim_time, 500)
                sol = self.dynamic_sim.simulate_rk45(
                    (0, sim_time), initial_state, voltage, freq,
                    load_torque_func, t_eval)
                t = sol.t
                omega = sol.y[0]
                theta = sol.y[1]
                T_temp = sol.y[2]
            else:  # Euler
                t, x = self.dynamic_sim.simulate_euler(
                    (0, sim_time), initial_state, voltage, freq,
                    load_torque_func, dt=0.01)
                omega = x[:, 0]
                theta = x[:, 1]
                T_temp = x[:, 2]

            # Convert speed to rpm
            speed_rpm = omega * 60 / (2 * np.pi)

            # Calculate torque and current for each time point
            torques = []
            currents = []

            for i, spd in enumerate(speed_rpm):
                slip = self.motor_model.calculate_slip(spd, freq)
                I, T = self.motor_model.calculate_current_torque(voltage, freq, slip)

                if self.motor_params.connection.lower() == "delta":
                    I_line = np.sqrt(3) * I
                else:
                    I_line = I

                torques.append(T)
                currents.append(I_line)

            torques = np.array(torques)
            currents = np.array(currents)

            # Update plots
            self.root.after(0, self.update_simulation_plots,
                          t, speed_rpm, torques, currents, T_temp)

        except Exception as e:
            self.root.after(0, messagebox.showerror, "Error",
                          f"Simulation error:\n{str(e)}")
        finally:
            self.root.after(0, self.stop_simulation)

    def update_simulation_plots(self, t, speed, torque, current, temperature):
        """Update simulation plots"""
        try:
            # Speed
            self.sim_ax1.clear()
            self.sim_ax1.plot(t, speed, 'b-', linewidth=2)
            self.sim_ax1.set_title('Speed vs Time')
            self.sim_ax1.set_xlabel('Time (s)')
            self.sim_ax1.set_ylabel('Speed (rpm)')
            self.sim_ax1.grid(True, alpha=0.3)

            # Torque
            self.sim_ax2.clear()
            self.sim_ax2.plot(t, torque, 'r-', linewidth=2)
            self.sim_ax2.set_title('Torque vs Time')
            self.sim_ax2.set_xlabel('Time (s)')
            self.sim_ax2.set_ylabel('Torque (Nm)')
            self.sim_ax2.grid(True, alpha=0.3)

            # Current
            self.sim_ax3.clear()
            self.sim_ax3.plot(t, current, 'g-', linewidth=2)
            self.sim_ax3.set_title('Current vs Time')
            self.sim_ax3.set_xlabel('Time (s)')
            self.sim_ax3.set_ylabel('Current (A)')
            self.sim_ax3.grid(True, alpha=0.3)

            # Temperature
            self.sim_ax4.clear()
            self.sim_ax4.plot(t, temperature, 'm-', linewidth=2)
            self.sim_ax4.axhline(y=155, color='r', linestyle='--', label='Class F limit')
            self.sim_ax4.set_title('Temperature vs Time')
            self.sim_ax4.set_xlabel('Time (s)')
            self.sim_ax4.set_ylabel('Temperature (°C)')
            self.sim_ax4.grid(True, alpha=0.3)
            self.sim_ax4.legend()

            self.sim_fig.tight_layout()
            self.sim_canvas.draw()

        except Exception as e:
            print(f"Error updating plots: {e}")

    def run_multiphysics(self):
        """Run multi-physics analysis"""
        try:
            speed_rpm = self.mp_speed_var.get()
            freq = self.freq_var.get()
            voltage = self.voltage_var.get()

            # Calculate operating point
            slip = self.motor_model.calculate_slip(speed_rpm, freq)
            I1, T_em = self.motor_model.calculate_current_torque(voltage, freq, slip)

            # Angular velocity
            omega = speed_rpm * 2 * np.pi / 60

            # Assume initial temperature
            T_temp = 75  # °C

            # Calculate I2 (rotor current)
            freq_ratio = freq / self.motor_params.frequency_rated
            Xm = self.motor_params.Xm * freq_ratio
            X2 = self.motor_params.X2_prime * freq_ratio

            if abs(slip) > 1e-6:
                I2_squared = (I1**2 * Xm**2) / \
                            ((self.motor_params.R2_prime/slip)**2 + X2**2)
                I2 = np.sqrt(I2_squared)
            else:
                I2 = 0

            # Calculate detailed losses
            losses = self.multiphysics_sim.calculate_detailed_losses(
                I1, I2, freq, omega, T_temp)

            # Display losses
            self.losses_text.delete('1.0', tk.END)

            output = "="*70 + "\n"
            output += "DETAILED LOSS BREAKDOWN\n"
            output += "="*70 + "\n\n"
            output += f"Operating Point:\n"
            output += f"  Speed: {speed_rpm:.1f} rpm\n"
            output += f"  Frequency: {freq:.1f} Hz\n"
            output += f"  Slip: {slip:.4f}\n"
            output += f"  Electromagnetic Torque: {T_em:.2f} Nm\n\n"

            output += "Copper Losses:\n"
            output += f"  Stator: {losses['copper_stator']:.2f} W\n"
            output += f"  Rotor: {losses['copper_rotor']:.2f} W\n"
            output += f"  Total: {losses['copper_total']:.2f} W\n\n"

            output += "Iron Losses:\n"
            output += f"  Hysteresis: {losses['hysteresis']:.2f} W\n"
            output += f"  Eddy Current: {losses['eddy_current']:.2f} W\n"
            output += f"  Total: {losses['iron_total']:.2f} W\n\n"

            output += "Mechanical Losses:\n"
            output += f"  Friction: {losses['friction']:.2f} W\n"
            output += f"  Windage: {losses['windage']:.2f} W\n"
            output += f"  Total: {losses['mechanical_total']:.2f} W\n\n"

            output += f"Stray Load Losses: {losses['stray_load']:.2f} W\n\n"
            output += f"TOTAL LOSSES: {losses['total']:.2f} W\n\n"

            # Calculate efficiency
            P_out = T_em * omega
            efficiency = self.economic.calculate_efficiency(P_out, losses['total'])
            output += f"Output Power: {P_out:.2f} W ({P_out/1000:.2f} kW)\n"
            output += f"Efficiency: {efficiency*100:.2f}%\n"

            self.losses_text.insert('1.0', output)

            # Thermal analysis
            thermal = self.multiphysics_sim.calculate_thermal_distribution(
                losses, self.motor_params.ambient_temp)

            # Plot thermal distribution
            self.thermal_ax.clear()

            components = ['Frame', 'Stator', 'Rotor']
            temperatures = [thermal['frame'], thermal['stator'], thermal['rotor']]
            colors = ['#3498db', '#e74c3c', '#f39c12']

            bars = self.thermal_ax.bar(components, temperatures, color=colors, alpha=0.7)
            self.thermal_ax.axhline(y=self.motor_params.ambient_temp,
                                   color='g', linestyle='--', label='Ambient')
            self.thermal_ax.axhline(y=155, color='r', linestyle='--',
                                   label='Class F Limit (155°C)')

            self.thermal_ax.set_ylabel('Temperature (°C)', fontsize=12)
            self.thermal_ax.set_title('Temperature Distribution',
                                     fontsize=14, fontweight='bold')
            self.thermal_ax.legend()
            self.thermal_ax.grid(True, alpha=0.3, axis='y')

            # Add value labels on bars
            for bar, temp in zip(bars, temperatures):
                height = bar.get_height()
                self.thermal_ax.text(bar.get_x() + bar.get_width()/2., height,
                                    f'{temp:.1f}°C',
                                    ha='center', va='bottom', fontweight='bold')

            self.thermal_fig.tight_layout()
            self.thermal_canvas.draw()

            # Mechanical stress analysis
            alpha_accel = 0  # Steady state
            stress = self.multiphysics_sim.calculate_mechanical_stress(
                T_em, omega, alpha_accel)

            self.stress_text.delete('1.0', tk.END)

            output = "="*70 + "\n"
            output += "MECHANICAL STRESS ANALYSIS\n"
            output += "="*70 + "\n\n"
            output += f"Shaft Torque: {stress['shaft_torque']:.2f} Nm\n"
            output += f"Shaft Stress: {stress['shaft_stress']/1e6:.2f} MPa\n\n"
            output += "Bearing Loads:\n"
            output += f"  Radial Load: {stress['bearing_radial']:.2f} N\n"
            output += f"  Axial Load: {stress['bearing_axial']:.2f} N\n"
            output += f"  Dynamic Load: {stress['dynamic_load']:.2f} N\n"
            output += f"  Total Load: {stress['bearing_total']:.2f} N\n"

            self.stress_text.insert('1.0', output)

            # Derating analysis
            altitude = self.altitude_var.get()
            voltage_var = self.voltage_variation_var.get() / 100

            derating = self.multiphysics_sim.calculate_derating(
                thermal['max'], altitude, voltage_var)

            self.derating_text.delete('1.0', tk.END)

            output = "="*70 + "\n"
            output += "DERATING ANALYSIS\n"
            output += "="*70 + "\n\n"
            output += f"Maximum Temperature: {thermal['max']:.1f} °C\n"
            output += f"Altitude: {altitude:.0f} m\n"
            output += f"Voltage Variation: {voltage_var*100:.1f}%\n\n"
            output += "Derating Factors:\n"
            output += f"  Temperature: {derating['temperature']:.3f}\n"
            output += f"  Altitude: {derating['altitude']:.3f}\n"
            output += f"  Voltage: {derating['voltage']:.3f}\n\n"
            output += f"Overall Derating Factor: {derating['overall']:.3f}\n\n"
            output += f"Derated Power: {self.motor_params.power_rated * derating['overall'] / 1000:.2f} kW\n"
            output += f"(from rated {self.motor_params.power_rated/1000:.2f} kW)\n"

            self.derating_text.insert('1.0', output)

            messagebox.showinfo("Success", "Multi-physics analysis completed!")

        except Exception as e:
            messagebox.showerror("Error", f"Error in multi-physics analysis:\n{str(e)}")

    def calculate_economics(self):
        """Calculate economic metrics"""
        try:
            op_hours = self.op_hours_var.get()
            load_factor = self.load_factor_var.get()
            efficiency = self.efficiency_var.get()
            lifetime = int(self.lifetime_var.get())

            # Update electricity cost
            self.motor_params.electricity_cost = self.elec_cost_var.get()

            # Energy consumption
            energy = self.economic.calculate_energy_consumption(
                op_hours, load_factor, efficiency)

            self.energy_text.delete('1.0', tk.END)

            output = "="*70 + "\n"
            output += "ENERGY CONSUMPTION ANALYSIS\n"
            output += "="*70 + "\n\n"
            output += f"Motor Rated Power: {self.motor_params.power_rated/1000:.2f} kW\n"
            output += f"Operating Hours/Year: {op_hours:.0f} hours\n"
            output += f"Average Load Factor: {load_factor:.2f}\n"
            output += f"Efficiency: {efficiency*100:.1f}%\n"
            output += f"Electricity Cost: ${self.motor_params.electricity_cost:.3f}/kWh\n\n"
            output += f"Average Output Power: {self.motor_params.power_rated * load_factor / 1000:.2f} kW\n"
            output += f"Average Input Power: {self.motor_params.power_rated * load_factor / efficiency / 1000:.2f} kW\n\n"
            output += f"Annual Energy Consumption: {energy['energy_kwh']:.0f} kWh\n"
            output += f"Annual Energy Cost: ${energy['cost_annual']:.2f}\n"

            self.energy_text.insert('1.0', output)

            # Lifecycle cost
            lcc = self.economic.calculate_lifecycle_cost(
                lifetime, op_hours, load_factor, efficiency)

            self.lcc_text.delete('1.0', tk.END)

            output = "="*70 + "\n"
            output += "LIFECYCLE COST ANALYSIS\n"
            output += "="*70 + "\n\n"
            output += f"Analysis Period: {lifetime} years\n"
            output += f"Discount Rate: 5%\n\n"
            output += "Cost Breakdown:\n"
            output += f"  Initial Cost: ${lcc['initial_cost']:.2f}\n"
            output += f"  Annual Energy Cost: ${lcc['annual_energy_cost']:.2f}\n"
            output += f"  Annual Maintenance Cost: ${lcc['annual_maintenance_cost']:.2f}\n"
            output += f"  Total Annual Operating Cost: ${lcc['annual_energy_cost'] + lcc['annual_maintenance_cost']:.2f}\n\n"
            output += f"Present Value of Operating Costs: ${lcc['present_value_annual_costs']:.2f}\n\n"
            output += f"TOTAL LIFECYCLE COST: ${lcc['total_lifecycle_cost']:.2f}\n\n"
            output += "Cost Distribution:\n"
            pct_initial = lcc['initial_cost'] / lcc['total_lifecycle_cost'] * 100
            pct_operating = lcc['present_value_annual_costs'] / lcc['total_lifecycle_cost'] * 100
            output += f"  Initial: {pct_initial:.1f}%\n"
            output += f"  Operating: {pct_operating:.1f}%\n"

            self.lcc_text.insert('1.0', output)

        except Exception as e:
            messagebox.showerror("Error", f"Error calculating economics:\n{str(e)}")

    def calculate_payback(self):
        """Calculate payback period"""
        try:
            old_eff = self.old_eff_var.get()
            new_eff = self.new_eff_var.get()
            new_cost = self.new_cost_var.get()
            op_hours = self.op_hours_var.get()
            load_factor = self.load_factor_var.get()

            payback = self.economic.payback_analysis(
                old_eff, new_eff, new_cost, op_hours, load_factor)

            self.payback_text.delete('1.0', tk.END)

            output = "="*70 + "\n"
            output += "PAYBACK ANALYSIS - MOTOR REPLACEMENT\n"
            output += "="*70 + "\n\n"
            output += "Comparison:\n"
            output += f"  Old Motor Efficiency: {old_eff*100:.1f}%\n"
            output += f"  New Motor Efficiency: {new_eff*100:.1f}%\n"
            output += f"  Efficiency Improvement: {(new_eff-old_eff)*100:.1f}%\n\n"
            output += "Operating Conditions:\n"
            output += f"  Operating Hours/Year: {op_hours:.0f} hours\n"
            output += f"  Average Load Factor: {load_factor:.2f}\n"
            output += f"  Electricity Cost: ${self.motor_params.electricity_cost:.3f}/kWh\n\n"
            output += "Annual Energy Costs:\n"
            output += f"  Old Motor: ${payback['old_energy_cost']:.2f}/year\n"
            output += f"  New Motor: ${payback['new_energy_cost']:.2f}/year\n"
            output += f"  Annual Savings: ${payback['annual_savings']:.2f}/year\n\n"
            output += f"Investment Required: ${payback['investment']:.2f}\n\n"

            if payback['payback_years'] < 100:
                output += f"SIMPLE PAYBACK PERIOD: {payback['payback_years']:.2f} years\n\n"

                if payback['payback_years'] < 3:
                    output += "RECOMMENDATION: Excellent investment - very short payback period\n"
                elif payback['payback_years'] < 5:
                    output += "RECOMMENDATION: Good investment - reasonable payback period\n"
                elif payback['payback_years'] < 10:
                    output += "RECOMMENDATION: Acceptable investment for long-term operation\n"
                else:
                    output += "RECOMMENDATION: Marginal investment - consider other factors\n"
            else:
                output += "PAYBACK PERIOD: Not economically viable\n"
                output += "New motor does not provide sufficient energy savings\n"

            self.payback_text.insert('1.0', output)

        except Exception as e:
            messagebox.showerror("Error", f"Error calculating payback:\n{str(e)}")

    def export_results(self):
        """Export all results"""
        messagebox.showinfo("Export", "Export functionality - save results to file")

    def load_parameters(self):
        """Load parameters from file"""
        messagebox.showinfo("Load", "Load parameters functionality")

    def save_results(self):
        """Save results to file"""
        messagebox.showinfo("Save", "Save results functionality")

    def show_about(self):
        """Show about dialog"""
        about_text = """Advanced Induction Motor Analysis Tool

Version: 1.0
Author: Electrical Engineering Department

This comprehensive tool provides:
- Solution to Example 6.3
- Dynamic simulation with ODE solvers
- Multi-physics analysis (electromagnetic-thermal-mechanical)
- Economic analysis and lifecycle costing
- Advanced control methods
- Real-time visualization

For support and documentation, contact support@example.com
"""
        messagebox.showinfo("About", about_text)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    root = tk.Tk()
    app = InductionMotorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
