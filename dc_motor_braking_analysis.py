"""
DC Motor Braking Analysis Application
Advanced Multi-Physics Simulation with Tkinter GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy.integrate import solve_ivp, odeint
import math
from dataclasses import dataclass
from typing import Tuple, List, Dict
import threading
import time


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
        # Approximation: Proportional to speed^1.5 and flux^2
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
        # Shaft stress calculation (simplified)
        # Assuming solid shaft with diameter proportional to torque
        shaft_diameter = 0.05  # meters (50mm assumed)

        # Torsional shear stress: τ = (16 * T) / (π * d^3)
        torsional_stress = (16 * abs(torque)) / (math.pi * shaft_diameter**3)

        # Bearing load (simplified - assuming radial load from weight)
        bearing_radial_load = 500  # N (assumed)

        # Bearing thrust load from electromagnetic forces
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
        self.time_history = []
        self.state_history = []
        self.running = False

    def coupled_equations(self, t: float, y: np.ndarray) -> np.ndarray:
        """
        Coupled electromagnetic-thermal-mechanical differential equations
        State vector y = [omega, theta, I_a, T_motor, Q_heat]
        omega: angular velocity (rad/s)
        theta: angular position (rad)
        I_a: armature current (A)
        T_motor: motor temperature (C)
        Q_heat: accumulated heat (J)
        """
        omega, theta, I_a, T_motor, Q_heat = y

        p = self.params

        # Convert speed to RPM for calculations
        speed_rpm = omega * 60 / (2 * math.pi)

        # Back EMF
        Eb = self.calc.k_phi * omega

        # Get external resistance
        R_ext = self.calc.results.get('plugging_resistance', 0)

        # Electromagnetic equation: V_applied = I_a * (Ra + R_ext) + Eb
        # During plugging, voltage is reversed
        if omega > 0:  # Still rotating forward, plugging applies
            V_applied = -p.voltage  # Reversed
        else:
            V_applied = 0  # Motor stopped

        # Temperature-dependent resistance
        temp_coefficient = 0.00393
        Ra_temp = p.armature_resistance * (1 + temp_coefficient * (T_motor - 25))

        # Current derivative (electrical transient) - simplified first order
        tau_electrical = 0.01  # Electrical time constant (s)
        I_target = (V_applied - Eb) / (Ra_temp + R_ext) if (Ra_temp + R_ext) > 0 else 0
        dI_dt = (I_target - I_a) / tau_electrical

        # Electromagnetic torque
        T_em = self.calc.k_phi * I_a

        # Load torque (braking torque)
        T_load = -T_em if omega > 0 else 0

        # Friction torque
        T_friction = p.friction_coefficient * omega

        # Mechanical equation: J * dω/dt = T_em - T_friction
        domega_dt = (T_load - T_friction) / p.moment_of_inertia

        # Angular position
        dtheta_dt = omega

        # Thermal equations
        # Calculate losses
        losses = self.calc.calculate_losses(I_a, speed_rpm, T_motor)
        P_loss = losses['total_loss']

        # Heat transfer: Q = (T_motor - T_ambient) / R_thermal
        Q_dissipated = (T_motor - p.ambient_temp) / p.thermal_resistance

        # Temperature rise: C_thermal * dT/dt = P_loss - Q_dissipated
        dT_dt = (P_loss - Q_dissipated) / p.thermal_capacitance

        # Heat accumulation
        dQ_dt = P_loss

        # Stop simulation when motor stops
        if omega <= 0 and domega_dt <= 0:
            domega_dt = 0
            dtheta_dt = 0
            dI_dt = 0

        return np.array([domega_dt, dtheta_dt, dI_dt, dT_dt, dQ_dt])

    def simulate_rk45(self, t_span: Tuple[float, float], method='RK45') -> Dict:
        """Run simulation using scipy's solve_ivp with specified method"""
        # Initial conditions
        omega_0 = self.calc.omega_full_load
        theta_0 = 0
        I_a_0 = self.params.full_load_current
        T_motor_0 = self.params.ambient_temp + 20  # Initial temperature rise
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

    def simulate_euler(self, t_span: Tuple[float, float], dt: float = 0.001) -> Dict:
        """Run simulation using Euler method"""
        t_start, t_end = t_span
        n_steps = int((t_end - t_start) / dt)

        # Initialize arrays
        time = np.linspace(t_start, t_end, n_steps)
        omega = np.zeros(n_steps)
        theta = np.zeros(n_steps)
        current = np.zeros(n_steps)
        temperature = np.zeros(n_steps)
        heat = np.zeros(n_steps)

        # Initial conditions
        omega[0] = self.calc.omega_full_load
        theta[0] = 0
        current[0] = self.params.full_load_current
        temperature[0] = self.params.ambient_temp + 20
        heat[0] = 0

        # Euler integration
        for i in range(n_steps - 1):
            y = np.array([omega[i], theta[i], current[i], temperature[i], heat[i]])
            dydt = self.coupled_equations(time[i], y)

            omega[i+1] = omega[i] + dydt[0] * dt
            theta[i+1] = theta[i] + dydt[1] * dt
            current[i+1] = current[i] + dydt[2] * dt
            temperature[i+1] = temperature[i] + dydt[3] * dt
            heat[i+1] = heat[i] + dydt[4] * dt

            # Stop if motor stopped
            if omega[i+1] <= 0:
                omega[i+1:] = 0
                break

        results = {
            'time': time,
            'omega': omega,
            'speed_rpm': omega * 60 / (2 * math.pi),
            'theta': theta,
            'current': current,
            'temperature': temperature,
            'heat': heat,
            'success': True,
            'message': 'Euler method completed'
        }

        # Calculate derived quantities
        results['torque'] = self.calc.k_phi * results['current']
        results['power'] = results['torque'] * results['omega']

        return results


class EconomicAnalyzer:
    """Economic analysis module"""

    def __init__(self, calculator: DCMotorBrakingCalculator):
        self.calc = calculator

    def calculate_energy_costs(self, simulation_results: Dict,
                             electricity_rate: float = 0.12) -> Dict:
        """Calculate energy consumption and costs"""
        # Energy consumed (kWh)
        time = simulation_results['time']
        power = simulation_results['power']

        # Integrate power over time to get energy
        energy_j = np.trapz(np.abs(power), time)
        energy_kwh = energy_j / (3600 * 1000)

        # Cost
        cost = energy_kwh * electricity_rate

        # Peak power
        peak_power_kw = np.max(np.abs(power)) / 1000

        return {
            'energy_kwh': energy_kwh,
            'cost_usd': cost,
            'peak_power_kw': peak_power_kw,
            'electricity_rate': electricity_rate
        }

    def calculate_lifetime_costs(self, operating_hours_per_year: float,
                                years: int, maintenance_cost_per_year: float) -> Dict:
        """Calculate lifetime costs"""
        energy_per_operation = 0.1  # kWh (estimated)
        operations_per_hour = 10  # Braking operations per hour

        annual_energy = energy_per_operation * operations_per_hour * operating_hours_per_year
        annual_energy_cost = annual_energy * 0.12  # $/kWh

        total_energy_cost = annual_energy_cost * years
        total_maintenance_cost = maintenance_cost_per_year * years

        # Component replacement costs
        replacement_cost = 5000  # $ (estimated)
        replacements = years // 5  # Replace every 5 years
        total_replacement_cost = replacement_cost * replacements

        total_cost = total_energy_cost + total_maintenance_cost + total_replacement_cost

        return {
            'annual_energy_kwh': annual_energy,
            'annual_energy_cost': annual_energy_cost,
            'annual_maintenance_cost': maintenance_cost_per_year,
            'total_energy_cost': total_energy_cost,
            'total_maintenance_cost': total_maintenance_cost,
            'total_replacement_cost': total_replacement_cost,
            'total_lifetime_cost': total_cost,
            'years': years
        }


class DCMotorBrakingGUI:
    """Main GUI Application"""

    def __init__(self, root):
        self.root = root
        self.root.title("DC Motor Braking Analysis - Advanced Multi-Physics Simulator")
        self.root.geometry("1400x900")

        # Initialize parameters
        self.params = MotorParameters()
        self.calculator = DCMotorBrakingCalculator(self.params)
        self.simulator = MultiPhysicsSimulator(self.calculator)
        self.economic = EconomicAnalyzer(self.calculator)

        self.simulation_results = None
        self.simulation_running = False

        # Setup GUI
        self.setup_menu()
        self.setup_main_interface()

        # Bind resize event for auto-scaling
        self.root.bind('<Configure>', self.on_window_resize)

    def setup_menu(self):
        """Setup menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Analysis", command=self.reset_analysis)
        file_menu.add_command(label="Save Results", command=self.save_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def setup_main_interface(self):
        """Setup main interface with tabs"""
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Create tabs
        self.setup_input_tab()
        self.setup_analysis_tab()
        self.setup_simulation_tab()
        self.setup_multiphysics_tab()
        self.setup_economic_tab()
        self.setup_losses_tab()

    def setup_input_tab(self):
        """Setup input parameters tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Input Parameters")

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

        # Title
        title_label = ttk.Label(scrollable_frame, text="DC Motor Parameters",
                               font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)

        # Parameter inputs with sliders
        self.param_vars = {}
        self.param_sliders = {}

        params_config = [
            ("Power (HP)", "power_hp", 1, 100, 37.5),
            ("Voltage (V)", "voltage", 100, 500, 220),
            ("Full Load Speed (RPM)", "full_load_speed", 100, 2000, 535),
            ("Armature Resistance (Ω)", "armature_resistance", 0.01, 1.0, 0.086),
            ("Full Load Current (A)", "full_load_current", 10, 500, 140),
            ("Target Braking Current (A)", "target_braking_current", 50, 500, 200),
            ("Moment of Inertia (kg.m²)", "moment_of_inertia", 0.1, 5.0, 0.5),
            ("Field Resistance (Ω)", "field_resistance", 10, 500, 100),
            ("Ambient Temperature (°C)", "ambient_temp", 0, 50, 25),
            ("Thermal Resistance (K/W)", "thermal_resistance", 0.5, 10, 2.0),
            ("Thermal Capacitance (J/K)", "thermal_capacitance", 100, 2000, 500),
            ("Friction Coefficient", "friction_coefficient", 0.001, 0.1, 0.01),
        ]

        row = 1
        for label, param_name, min_val, max_val, default in params_config:
            # Label
            ttk.Label(scrollable_frame, text=label).grid(row=row, column=0,
                                                         sticky='w', padx=10, pady=5)

            # Entry
            var = tk.DoubleVar(value=default)
            entry = ttk.Entry(scrollable_frame, textvariable=var, width=15)
            entry.grid(row=row, column=1, padx=10, pady=5)
            self.param_vars[param_name] = var

            # Slider
            slider = ttk.Scale(scrollable_frame, from_=min_val, to=max_val,
                             orient='horizontal', length=300,
                             command=lambda val, v=var: v.set(float(val)))
            slider.set(default)
            slider.grid(row=row, column=2, padx=10, pady=5)
            self.param_sliders[param_name] = slider

            # Link slider to entry
            var.trace('w', lambda *args, s=slider, v=var: s.set(v.get()))

            row += 1

        # Calculate button
        calc_button = ttk.Button(scrollable_frame, text="Calculate Plugging Resistance",
                                command=self.calculate_plugging, style='Accent.TButton')
        calc_button.grid(row=row, column=0, columnspan=3, pady=20)

        # Results display
        row += 1
        results_frame = ttk.LabelFrame(scrollable_frame, text="Analytical Results",
                                      padding=10)
        results_frame.grid(row=row, column=0, columnspan=3, padx=10, pady=10,
                          sticky='ew')

        self.results_text = tk.Text(results_frame, height=15, width=70,
                                   font=('Courier', 10))
        self.results_text.pack(fill='both', expand=True)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def setup_analysis_tab(self):
        """Setup analysis and visualization tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Static Analysis")

        # Control frame
        control_frame = ttk.Frame(tab)
        control_frame.pack(side='top', fill='x', padx=10, pady=10)

        ttk.Label(control_frame, text="Speed Range Analysis",
                 font=('Arial', 12, 'bold')).pack(side='left', padx=10)

        ttk.Button(control_frame, text="Generate Curves",
                  command=self.generate_analysis_curves).pack(side='left', padx=5)

        # Matplotlib figure
        self.analysis_fig = Figure(figsize=(12, 8), dpi=100)
        self.analysis_canvas = FigureCanvasTkAgg(self.analysis_fig, tab)
        self.analysis_canvas.get_tk_widget().pack(fill='both', expand=True,
                                                 padx=10, pady=10)

    def setup_simulation_tab(self):
        """Setup dynamic simulation tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Dynamic Simulation")

        # Control frame
        control_frame = ttk.LabelFrame(tab, text="Simulation Controls", padding=10)
        control_frame.pack(side='top', fill='x', padx=10, pady=10)

        # Simulation method
        ttk.Label(control_frame, text="ODE Solver:").grid(row=0, column=0, padx=5)
        self.solver_var = tk.StringVar(value='RK45')
        solver_combo = ttk.Combobox(control_frame, textvariable=self.solver_var,
                                    values=['RK45', 'RK23', 'DOP853', 'Euler'],
                                    state='readonly', width=10)
        solver_combo.grid(row=0, column=1, padx=5)

        # Time span
        ttk.Label(control_frame, text="Simulation Time (s):").grid(row=0, column=2, padx=5)
        self.sim_time_var = tk.DoubleVar(value=5.0)
        ttk.Entry(control_frame, textvariable=self.sim_time_var,
                 width=10).grid(row=0, column=3, padx=5)

        # Buttons
        ttk.Button(control_frame, text="▶ Start Simulation",
                  command=self.start_simulation,
                  style='Accent.TButton').grid(row=0, column=4, padx=5)

        ttk.Button(control_frame, text="⏹ Stop",
                  command=self.stop_simulation).grid(row=0, column=5, padx=5)

        ttk.Button(control_frame, text="↻ Reset",
                  command=self.reset_simulation).grid(row=0, column=6, padx=5)

        # Status label
        self.sim_status_label = ttk.Label(control_frame, text="Ready",
                                         foreground='green')
        self.sim_status_label.grid(row=0, column=7, padx=10)

        # Matplotlib figure for simulation results
        self.sim_fig = Figure(figsize=(12, 8), dpi=100)
        self.sim_canvas = FigureCanvasTkAgg(self.sim_fig, tab)
        self.sim_canvas.get_tk_widget().pack(fill='both', expand=True,
                                            padx=10, pady=10)

    def setup_multiphysics_tab(self):
        """Setup multi-physics simulation tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Multi-Physics")

        # Info label
        info_frame = ttk.Frame(tab)
        info_frame.pack(side='top', fill='x', padx=10, pady=5)

        ttk.Label(info_frame,
                 text="Coupled Electromagnetic-Thermal-Mechanical Analysis",
                 font=('Arial', 12, 'bold')).pack()

        # Matplotlib figure
        self.multiphys_fig = Figure(figsize=(12, 8), dpi=100)
        self.multiphys_canvas = FigureCanvasTkAgg(self.multiphys_fig, tab)
        self.multiphys_canvas.get_tk_widget().pack(fill='both', expand=True,
                                                   padx=10, pady=10)

    def setup_economic_tab(self):
        """Setup economic analysis tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Economic Analysis")

        # Input frame
        input_frame = ttk.LabelFrame(tab, text="Economic Parameters", padding=10)
        input_frame.pack(side='top', fill='x', padx=10, pady=10)

        # Electricity rate
        ttk.Label(input_frame, text="Electricity Rate ($/kWh):").grid(row=0, column=0,
                                                                     padx=5, pady=5)
        self.elec_rate_var = tk.DoubleVar(value=0.12)
        ttk.Entry(input_frame, textvariable=self.elec_rate_var,
                 width=15).grid(row=0, column=1, padx=5, pady=5)

        # Operating hours
        ttk.Label(input_frame, text="Operating Hours/Year:").grid(row=0, column=2,
                                                                  padx=5, pady=5)
        self.op_hours_var = tk.DoubleVar(value=4000)
        ttk.Entry(input_frame, textvariable=self.op_hours_var,
                 width=15).grid(row=0, column=3, padx=5, pady=5)

        # Years
        ttk.Label(input_frame, text="Lifetime (years):").grid(row=1, column=0,
                                                              padx=5, pady=5)
        self.years_var = tk.IntVar(value=10)
        ttk.Entry(input_frame, textvariable=self.years_var,
                 width=15).grid(row=1, column=1, padx=5, pady=5)

        # Maintenance cost
        ttk.Label(input_frame, text="Maintenance Cost ($/year):").grid(row=1, column=2,
                                                                       padx=5, pady=5)
        self.maint_cost_var = tk.DoubleVar(value=1000)
        ttk.Entry(input_frame, textvariable=self.maint_cost_var,
                 width=15).grid(row=1, column=3, padx=5, pady=5)

        # Calculate button
        ttk.Button(input_frame, text="Calculate Economics",
                  command=self.calculate_economics).grid(row=2, column=0,
                                                         columnspan=4, pady=10)

        # Results display
        results_frame = ttk.LabelFrame(tab, text="Economic Results", padding=10)
        results_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.economic_text = tk.Text(results_frame, height=15,
                                    font=('Courier', 10))
        self.economic_text.pack(fill='both', expand=True)

        # Chart frame
        self.economic_fig = Figure(figsize=(10, 4), dpi=100)
        self.economic_canvas = FigureCanvasTkAgg(self.economic_fig, results_frame)
        self.economic_canvas.get_tk_widget().pack(fill='both', expand=True)

    def setup_losses_tab(self):
        """Setup detailed losses breakdown tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Loss Analysis")

        # Info
        ttk.Label(tab, text="Detailed Loss Breakdown and Efficiency Analysis",
                 font=('Arial', 12, 'bold')).pack(pady=10)

        # Matplotlib figure
        self.losses_fig = Figure(figsize=(12, 8), dpi=100)
        self.losses_canvas = FigureCanvasTkAgg(self.losses_fig, tab)
        self.losses_canvas.get_tk_widget().pack(fill='both', expand=True,
                                               padx=10, pady=10)

    def update_parameters(self):
        """Update motor parameters from GUI inputs"""
        self.params.power_hp = self.param_vars['power_hp'].get()
        self.params.voltage = self.param_vars['voltage'].get()
        self.params.full_load_speed = self.param_vars['full_load_speed'].get()
        self.params.armature_resistance = self.param_vars['armature_resistance'].get()
        self.params.full_load_current = self.param_vars['full_load_current'].get()
        self.params.target_braking_current = self.param_vars['target_braking_current'].get()
        self.params.moment_of_inertia = self.param_vars['moment_of_inertia'].get()
        self.params.field_resistance = self.param_vars['field_resistance'].get()
        self.params.ambient_temp = self.param_vars['ambient_temp'].get()
        self.params.thermal_resistance = self.param_vars['thermal_resistance'].get()
        self.params.thermal_capacitance = self.param_vars['thermal_capacitance'].get()
        self.params.friction_coefficient = self.param_vars['friction_coefficient'].get()

        # Recreate calculator with new parameters
        self.calculator = DCMotorBrakingCalculator(self.params)
        self.simulator = MultiPhysicsSimulator(self.calculator)
        self.economic = EconomicAnalyzer(self.calculator)

    def calculate_plugging(self):
        """Calculate plugging resistance and braking torques"""
        self.update_parameters()

        # Calculate plugging resistance
        R_ext = self.calculator.calculate_plugging_resistance()

        # Calculate initial braking torque
        T_initial, I_initial = self.calculator.calculate_braking_torque(
            self.params.full_load_speed, R_ext
        )

        # Calculate braking torque at half speed
        T_half, I_half = self.calculator.calculate_braking_torque(
            self.params.full_load_speed / 2, R_ext
        )

        # Mechanical stress analysis
        stress_initial = self.calculator.mechanical_stress_analysis(T_initial)
        stress_half = self.calculator.mechanical_stress_analysis(T_half)

        # Format results
        results_text = f"""
{'='*70}
DC MOTOR BRAKING ANALYSIS RESULTS
{'='*70}

MOTOR SPECIFICATIONS:
  Power Rating:           {self.params.power_hp:.1f} HP ({self.calculator.power_watts:.1f} W)
  Voltage:                {self.params.voltage:.1f} V
  Full Load Speed:        {self.params.full_load_speed:.1f} RPM ({self.calculator.omega_full_load:.2f} rad/s)
  Armature Resistance:    {self.params.armature_resistance:.4f} Ω
  Full Load Current:      {self.params.full_load_current:.1f} A
  Target Braking Current: {self.params.target_braking_current:.1f} A

DERIVED PARAMETERS:
  Back EMF (Full Load):   {self.calculator.Eb_full_load:.2f} V
  Motor Constant (k·φ):   {self.calculator.k_phi:.4f} V·s/rad
  Full Load Torque:       {self.calculator.torque_full_load:.2f} N·m

{'='*70}
PLUGGING RESISTANCE CALCULATION:
{'='*70}
  External Resistance Required:  {R_ext:.4f} Ω
  Total Circuit Resistance:      {self.calculator.results['total_resistance']:.4f} Ω

{'='*70}
BRAKING TORQUE ANALYSIS:
{'='*70}

INITIAL BRAKING (At Full Load Speed = {self.params.full_load_speed:.1f} RPM):
  Braking Current:        {I_initial:.2f} A
  Braking Torque:         {T_initial:.2f} N·m
  Braking Power:          {T_initial * self.calculator.omega_full_load / 1000:.2f} kW

AT HALF SPEED ({self.params.full_load_speed/2:.1f} RPM):
  Braking Current:        {I_half:.2f} A
  Braking Torque:         {T_half:.2f} N·m
  Braking Power:          {T_half * self.calculator.omega_full_load / 2 / 1000:.2f} kW

TORQUE REDUCTION:         {((T_initial - T_half) / T_initial * 100):.1f}%

{'='*70}
MECHANICAL STRESS ANALYSIS:
{'='*70}

INITIAL CONDITIONS:
  Torsional Stress:       {stress_initial['torsional_stress_MPa']:.2f} MPa
  Bearing Radial Load:    {stress_initial['bearing_radial_load_N']:.1f} N
  Bearing Thrust Load:    {stress_initial['bearing_thrust_load_N']:.1f} N
  Shaft Diameter:         {stress_initial['shaft_diameter_mm']:.1f} mm

AT HALF SPEED:
  Torsional Stress:       {stress_half['torsional_stress_MPa']:.2f} MPa
  Bearing Radial Load:    {stress_half['bearing_radial_load_N']:.1f} N
  Bearing Thrust Load:    {stress_half['bearing_thrust_load_N']:.1f} N

{'='*70}
SAFETY NOTES:
{'='*70}
- Plugging produces high mechanical stresses
- Ensure adequate cooling during braking
- Check shaft and bearing ratings
- Monitor temperature rise during operation
{'='*70}
"""

        self.results_text.delete('1.0', tk.END)
        self.results_text.insert('1.0', results_text)

    def generate_analysis_curves(self):
        """Generate static analysis curves"""
        self.update_parameters()

        # Calculate plugging resistance
        R_ext = self.calculator.calculate_plugging_resistance()

        # Speed range from full load to zero
        speeds = np.linspace(self.params.full_load_speed, 0, 100)
        torques = []
        currents = []
        powers = []

        for speed in speeds:
            T, I = self.calculator.calculate_braking_torque(speed, R_ext)
            omega = speed * 2 * math.pi / 60
            P = T * omega
            torques.append(T)
            currents.append(I)
            powers.append(P / 1000)  # kW

        # Clear previous plots
        self.analysis_fig.clear()

        # Create subplots
        ax1 = self.analysis_fig.add_subplot(2, 2, 1)
        ax2 = self.analysis_fig.add_subplot(2, 2, 2)
        ax3 = self.analysis_fig.add_subplot(2, 2, 3)
        ax4 = self.analysis_fig.add_subplot(2, 2, 4)

        # Plot 1: Torque vs Speed
        ax1.plot(speeds, torques, 'b-', linewidth=2)
        ax1.set_xlabel('Speed (RPM)', fontsize=10)
        ax1.set_ylabel('Braking Torque (N·m)', fontsize=10)
        ax1.set_title('Braking Torque vs Speed', fontsize=11, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=0, color='k', linestyle='--', linewidth=0.5)

        # Plot 2: Current vs Speed
        ax2.plot(speeds, currents, 'r-', linewidth=2)
        ax2.set_xlabel('Speed (RPM)', fontsize=10)
        ax2.set_ylabel('Braking Current (A)', fontsize=10)
        ax2.set_title('Braking Current vs Speed', fontsize=11, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=self.params.target_braking_current, color='g',
                   linestyle='--', linewidth=1, label='Target Current')
        ax2.legend()

        # Plot 3: Power vs Speed
        ax3.plot(speeds, powers, 'g-', linewidth=2)
        ax3.set_xlabel('Speed (RPM)', fontsize=10)
        ax3.set_ylabel('Braking Power (kW)', fontsize=10)
        ax3.set_title('Braking Power vs Speed', fontsize=11, fontweight='bold')
        ax3.grid(True, alpha=0.3)

        # Plot 4: Energy dissipation
        # Calculate cumulative energy
        time_est = np.linspace(0, 5, len(speeds))  # Estimated time
        energy = np.cumsum(np.array(powers) * np.diff(time_est, prepend=0))
        ax4.plot(time_est, energy, 'm-', linewidth=2)
        ax4.set_xlabel('Time (s)', fontsize=10)
        ax4.set_ylabel('Energy Dissipated (kJ)', fontsize=10)
        ax4.set_title('Cumulative Energy Dissipation', fontsize=11, fontweight='bold')
        ax4.grid(True, alpha=0.3)

        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def start_simulation(self):
        """Start dynamic simulation"""
        if self.simulation_running:
            messagebox.showwarning("Warning", "Simulation already running!")
            return

        self.update_parameters()

        # Calculate plugging resistance first
        R_ext = self.calculator.calculate_plugging_resistance()

        # Update status
        self.sim_status_label.config(text="Simulating...", foreground='orange')
        self.simulation_running = True

        # Run simulation in thread to keep GUI responsive
        def run_sim():
            try:
                t_span = (0, self.sim_time_var.get())
                solver = self.solver_var.get()

                if solver == 'Euler':
                    results = self.simulator.simulate_euler(t_span)
                else:
                    results = self.simulator.simulate_rk45(t_span, method=solver)

                self.simulation_results = results

                # Update GUI in main thread
                self.root.after(0, self.display_simulation_results)
                self.root.after(0, lambda: self.sim_status_label.config(
                    text="Complete", foreground='green'))

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Simulation Error", str(e)))
                self.root.after(0, lambda: self.sim_status_label.config(
                    text="Error", foreground='red'))
            finally:
                self.simulation_running = False

        thread = threading.Thread(target=run_sim, daemon=True)
        thread.start()

    def stop_simulation(self):
        """Stop simulation"""
        self.simulation_running = False
        self.sim_status_label.config(text="Stopped", foreground='red')

    def reset_simulation(self):
        """Reset simulation"""
        self.simulation_running = False
        self.simulation_results = None
        self.sim_status_label.config(text="Reset", foreground='blue')
        self.sim_fig.clear()
        self.sim_canvas.draw()

    def display_simulation_results(self):
        """Display simulation results"""
        if self.simulation_results is None:
            return

        results = self.simulation_results

        # Clear previous plots
        self.sim_fig.clear()

        # Create subplots (3x2 grid)
        ax1 = self.sim_fig.add_subplot(3, 2, 1)
        ax2 = self.sim_fig.add_subplot(3, 2, 2)
        ax3 = self.sim_fig.add_subplot(3, 2, 3)
        ax4 = self.sim_fig.add_subplot(3, 2, 4)
        ax5 = self.sim_fig.add_subplot(3, 2, 5)
        ax6 = self.sim_fig.add_subplot(3, 2, 6)

        # Plot 1: Speed vs Time
        ax1.plot(results['time'], results['speed_rpm'], 'b-', linewidth=2)
        ax1.set_xlabel('Time (s)', fontsize=9)
        ax1.set_ylabel('Speed (RPM)', fontsize=9)
        ax1.set_title('Speed vs Time', fontsize=10, fontweight='bold')
        ax1.grid(True, alpha=0.3)

        # Plot 2: Current vs Time
        ax2.plot(results['time'], results['current'], 'r-', linewidth=2)
        ax2.set_xlabel('Time (s)', fontsize=9)
        ax2.set_ylabel('Current (A)', fontsize=9)
        ax2.set_title('Armature Current vs Time', fontsize=10, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        # Plot 3: Torque vs Time
        ax3.plot(results['time'], results['torque'], 'g-', linewidth=2)
        ax3.set_xlabel('Time (s)', fontsize=9)
        ax3.set_ylabel('Torque (N·m)', fontsize=9)
        ax3.set_title('Braking Torque vs Time', fontsize=10, fontweight='bold')
        ax3.grid(True, alpha=0.3)

        # Plot 4: Power vs Time
        power_kw = results['power'] / 1000
        ax4.plot(results['time'], power_kw, 'm-', linewidth=2)
        ax4.set_xlabel('Time (s)', fontsize=9)
        ax4.set_ylabel('Power (kW)', fontsize=9)
        ax4.set_title('Power vs Time', fontsize=10, fontweight='bold')
        ax4.grid(True, alpha=0.3)

        # Plot 5: Temperature vs Time
        ax5.plot(results['time'], results['temperature'], 'orange', linewidth=2)
        ax5.set_xlabel('Time (s)', fontsize=9)
        ax5.set_ylabel('Temperature (°C)', fontsize=9)
        ax5.set_title('Motor Temperature vs Time', fontsize=10, fontweight='bold')
        ax5.grid(True, alpha=0.3)

        # Plot 6: Energy vs Time
        energy_kj = results['heat'] / 1000
        ax6.plot(results['time'], energy_kj, 'brown', linewidth=2)
        ax6.set_xlabel('Time (s)', fontsize=9)
        ax6.set_ylabel('Energy (kJ)', fontsize=9)
        ax6.set_title('Heat Dissipated vs Time', fontsize=10, fontweight='bold')
        ax6.grid(True, alpha=0.3)

        self.sim_fig.tight_layout()
        self.sim_canvas.draw()

        # Update multi-physics tab
        self.display_multiphysics_results()

        # Update losses tab
        self.display_losses_results()

    def display_multiphysics_results(self):
        """Display multi-physics coupling results"""
        if self.simulation_results is None:
            return

        results = self.simulation_results

        # Clear previous plots
        self.multiphys_fig.clear()

        # Create 3D subplot for phase space
        from mpl_toolkits.mplot3d import Axes3D

        ax1 = self.multiphys_fig.add_subplot(2, 2, 1, projection='3d')
        ax2 = self.multiphys_fig.add_subplot(2, 2, 2)
        ax3 = self.multiphys_fig.add_subplot(2, 2, 3)
        ax4 = self.multiphys_fig.add_subplot(2, 2, 4)

        # Plot 1: 3D Phase Space (Speed, Current, Temperature)
        ax1.plot(results['speed_rpm'], results['current'],
                results['temperature'], 'b-', linewidth=2)
        ax1.set_xlabel('Speed (RPM)', fontsize=9)
        ax1.set_ylabel('Current (A)', fontsize=9)
        ax1.set_zlabel('Temp (°C)', fontsize=9)
        ax1.set_title('3D Phase Space', fontsize=10, fontweight='bold')

        # Plot 2: Electromagnetic coupling (Torque vs Current)
        ax2.scatter(results['current'], results['torque'],
                   c=results['time'], cmap='viridis', s=20)
        ax2.set_xlabel('Current (A)', fontsize=9)
        ax2.set_ylabel('Torque (N·m)', fontsize=9)
        ax2.set_title('Electromagnetic Coupling', fontsize=10, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        cbar2 = plt.colorbar(ax2.collections[0], ax=ax2)
        cbar2.set_label('Time (s)', fontsize=8)

        # Plot 3: Thermal coupling (Temperature vs Power Loss)
        if len(results['losses']) > 0:
            total_losses = [loss['total_loss'] for loss in results['losses']]
            ax3.plot(results['temperature'], total_losses, 'r-', linewidth=2)
            ax3.set_xlabel('Temperature (°C)', fontsize=9)
            ax3.set_ylabel('Total Loss (W)', fontsize=9)
            ax3.set_title('Thermal Coupling', fontsize=10, fontweight='bold')
            ax3.grid(True, alpha=0.3)

        # Plot 4: Mechanical coupling (Torque vs Speed)
        ax4.scatter(results['speed_rpm'], results['torque'],
                   c=results['temperature'], cmap='hot', s=20)
        ax4.set_xlabel('Speed (RPM)', fontsize=9)
        ax4.set_ylabel('Torque (N·m)', fontsize=9)
        ax4.set_title('Mechanical Coupling', fontsize=10, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        cbar4 = plt.colorbar(ax4.collections[0], ax=ax4)
        cbar4.set_label('Temp (°C)', fontsize=8)

        self.multiphys_fig.tight_layout()
        self.multiphys_canvas.draw()

    def display_losses_results(self):
        """Display detailed losses breakdown"""
        if self.simulation_results is None or len(self.simulation_results['losses']) == 0:
            return

        results = self.simulation_results
        losses = results['losses']

        # Extract loss components
        copper_losses = [loss['copper_loss'] for loss in losses]
        field_losses = [loss['field_loss'] for loss in losses]
        iron_losses = [loss['iron_loss'] for loss in losses]
        friction_losses = [loss['friction_loss'] for loss in losses]
        stray_losses = [loss['stray_loss'] for loss in losses]
        total_losses = [loss['total_loss'] for loss in losses]

        # Clear previous plots
        self.losses_fig.clear()

        # Create subplots
        ax1 = self.losses_fig.add_subplot(2, 2, 1)
        ax2 = self.losses_fig.add_subplot(2, 2, 2)
        ax3 = self.losses_fig.add_subplot(2, 2, 3)
        ax4 = self.losses_fig.add_subplot(2, 2, 4)

        # Plot 1: Stacked area chart of losses
        ax1.fill_between(results['time'], 0, copper_losses,
                        label='Copper', alpha=0.7, color='red')
        ax1.fill_between(results['time'], copper_losses,
                        np.array(copper_losses) + np.array(field_losses),
                        label='Field', alpha=0.7, color='blue')
        ax1.fill_between(results['time'],
                        np.array(copper_losses) + np.array(field_losses),
                        np.array(copper_losses) + np.array(field_losses) + np.array(iron_losses),
                        label='Iron', alpha=0.7, color='green')
        ax1.fill_between(results['time'],
                        np.array(copper_losses) + np.array(field_losses) + np.array(iron_losses),
                        np.array(copper_losses) + np.array(field_losses) + np.array(iron_losses) + np.array(friction_losses),
                        label='Friction', alpha=0.7, color='orange')
        ax1.fill_between(results['time'],
                        np.array(copper_losses) + np.array(field_losses) + np.array(iron_losses) + np.array(friction_losses),
                        total_losses,
                        label='Stray', alpha=0.7, color='purple')
        ax1.set_xlabel('Time (s)', fontsize=9)
        ax1.set_ylabel('Power Loss (W)', fontsize=9)
        ax1.set_title('Loss Breakdown vs Time', fontsize=10, fontweight='bold')
        ax1.legend(fontsize=8)
        ax1.grid(True, alpha=0.3)

        # Plot 2: Individual loss components
        ax2.plot(results['time'], copper_losses, label='Copper', linewidth=2)
        ax2.plot(results['time'], field_losses, label='Field', linewidth=2)
        ax2.plot(results['time'], iron_losses, label='Iron', linewidth=2)
        ax2.plot(results['time'], friction_losses, label='Friction', linewidth=2)
        ax2.plot(results['time'], stray_losses, label='Stray', linewidth=2)
        ax2.set_xlabel('Time (s)', fontsize=9)
        ax2.set_ylabel('Power Loss (W)', fontsize=9)
        ax2.set_title('Individual Loss Components', fontsize=10, fontweight='bold')
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)

        # Plot 3: Pie chart of average losses
        avg_copper = np.mean(copper_losses)
        avg_field = np.mean(field_losses)
        avg_iron = np.mean(iron_losses)
        avg_friction = np.mean(friction_losses)
        avg_stray = np.mean(stray_losses)

        labels = ['Copper', 'Field', 'Iron', 'Friction', 'Stray']
        sizes = [avg_copper, avg_field, avg_iron, avg_friction, avg_stray]
        colors = ['red', 'blue', 'green', 'orange', 'purple']

        ax3.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
               startangle=90)
        ax3.set_title('Average Loss Distribution', fontsize=10, fontweight='bold')

        # Plot 4: Efficiency vs Time
        power_input = np.abs(results['current'] * self.params.voltage)
        efficiency = (1 - np.array(total_losses) / power_input) * 100
        efficiency[power_input < 1] = 0  # Avoid division by zero

        ax4.plot(results['time'], efficiency, 'b-', linewidth=2)
        ax4.set_xlabel('Time (s)', fontsize=9)
        ax4.set_ylabel('Efficiency (%)', fontsize=9)
        ax4.set_title('Instantaneous Efficiency', fontsize=10, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        ax4.set_ylim([0, 100])

        self.losses_fig.tight_layout()
        self.losses_canvas.draw()

    def calculate_economics(self):
        """Calculate economic analysis"""
        if self.simulation_results is None:
            messagebox.showwarning("Warning",
                                 "Please run simulation first!")
            return

        # Calculate energy costs from simulation
        energy_results = self.economic.calculate_energy_costs(
            self.simulation_results,
            self.elec_rate_var.get()
        )

        # Calculate lifetime costs
        lifetime_results = self.economic.calculate_lifetime_costs(
            self.op_hours_var.get(),
            self.years_var.get(),
            self.maint_cost_var.get()
        )

        # Display results
        results_text = f"""
{'='*70}
ECONOMIC ANALYSIS RESULTS
{'='*70}

SINGLE BRAKING OPERATION:
  Energy Consumed:        {energy_results['energy_kwh']:.4f} kWh
  Cost per Operation:     ${energy_results['cost_usd']:.4f}
  Peak Power:             {energy_results['peak_power_kw']:.2f} kW

ANNUAL OPERATION:
  Operating Hours/Year:   {self.op_hours_var.get():.0f} hours
  Annual Energy:          {lifetime_results['annual_energy_kwh']:.1f} kWh
  Annual Energy Cost:     ${lifetime_results['annual_energy_cost']:.2f}
  Annual Maintenance:     ${lifetime_results['annual_maintenance_cost']:.2f}
  Total Annual Cost:      ${lifetime_results['annual_energy_cost'] + lifetime_results['annual_maintenance_cost']:.2f}

LIFETIME COSTS ({self.years_var.get()} YEARS):
  Total Energy Cost:      ${lifetime_results['total_energy_cost']:.2f}
  Total Maintenance:      ${lifetime_results['total_maintenance_cost']:.2f}
  Component Replacement:  ${lifetime_results['total_replacement_cost']:.2f}
  TOTAL LIFETIME COST:    ${lifetime_results['total_lifetime_cost']:.2f}

COST PER OPERATING HOUR:  ${lifetime_results['total_lifetime_cost'] / (self.op_hours_var.get() * self.years_var.get()):.4f}/hr

{'='*70}
"""

        self.economic_text.delete('1.0', tk.END)
        self.economic_text.insert('1.0', results_text)

        # Plot cost breakdown
        self.economic_fig.clear()

        ax1 = self.economic_fig.add_subplot(1, 2, 1)
        ax2 = self.economic_fig.add_subplot(1, 2, 2)

        # Pie chart of lifetime costs
        labels = ['Energy', 'Maintenance', 'Replacement']
        sizes = [
            lifetime_results['total_energy_cost'],
            lifetime_results['total_maintenance_cost'],
            lifetime_results['total_replacement_cost']
        ]
        colors = ['#ff9999', '#66b3ff', '#99ff99']

        ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
               startangle=90)
        ax1.set_title('Lifetime Cost Breakdown', fontsize=11, fontweight='bold')

        # Bar chart of annual costs over years
        years = list(range(1, self.years_var.get() + 1))
        annual_costs = [lifetime_results['annual_energy_cost'] +
                       lifetime_results['annual_maintenance_cost']] * self.years_var.get()

        # Add replacement costs every 5 years
        for i in range(len(annual_costs)):
            if (i + 1) % 5 == 0:
                annual_costs[i] += 5000

        ax2.bar(years, annual_costs, color='steelblue')
        ax2.set_xlabel('Year', fontsize=10)
        ax2.set_ylabel('Annual Cost ($)', fontsize=10)
        ax2.set_title('Annual Costs Over Lifetime', fontsize=11, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')

        self.economic_fig.tight_layout()
        self.economic_canvas.draw()

    def on_window_resize(self, event):
        """Handle window resize for auto-scaling"""
        # This is automatically handled by pack with fill='both' and expand=True
        pass

    def reset_analysis(self):
        """Reset all analysis"""
        self.simulation_results = None
        self.results_text.delete('1.0', tk.END)
        self.economic_text.delete('1.0', tk.END)

        # Clear all plots
        for fig in [self.analysis_fig, self.sim_fig, self.multiphys_fig,
                   self.losses_fig, self.economic_fig]:
            fig.clear()

        for canvas in [self.analysis_canvas, self.sim_canvas,
                      self.multiphys_canvas, self.losses_canvas,
                      self.economic_canvas]:
            canvas.draw()

        messagebox.showinfo("Reset", "All analysis data has been reset")

    def save_results(self):
        """Save results to file"""
        if self.simulation_results is None:
            messagebox.showwarning("Warning", "No results to save")
            return

        try:
            # Save to text file
            with open('braking_analysis_results.txt', 'w') as f:
                f.write(self.results_text.get('1.0', tk.END))
                f.write("\n\n")
                f.write(self.economic_text.get('1.0', tk.END))

            # Save simulation data to CSV
            import csv
            with open('braking_simulation_data.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Time', 'Speed', 'Current', 'Torque',
                               'Temperature', 'Power', 'Energy'])

                results = self.simulation_results
                for i in range(len(results['time'])):
                    writer.writerow([
                        results['time'][i],
                        results['speed_rpm'][i],
                        results['current'][i],
                        results['torque'][i],
                        results['temperature'][i],
                        results['power'][i],
                        results['heat'][i]
                    ])

            messagebox.showinfo("Success",
                              "Results saved to:\n" +
                              "- braking_analysis_results.txt\n" +
                              "- braking_simulation_data.csv")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save results: {str(e)}")

    def show_about(self):
        """Show about dialog"""
        about_text = """
DC Motor Braking Analysis Application
Version 1.0

Advanced Multi-Physics Simulation Tool

Features:
• Plugging resistance calculation
• Dynamic simulation with multiple ODE solvers
• Multi-physics coupling (EM-Thermal-Mechanical)
• Detailed loss breakdown
• Economic analysis
• Real-time visualization

Developed for advanced electrical engineering analysis
        """
        messagebox.showinfo("About", about_text)


def main():
    """Main entry point"""
    root = tk.Tk()

    # Configure ttk style
    style = ttk.Style()
    style.theme_use('clam')

    # Create custom style for accent buttons
    style.configure('Accent.TButton',
                   foreground='white',
                   background='#0066cc',
                   font=('Arial', 10, 'bold'))

    app = DCMotorBrakingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
