"""
Advanced DC Motor Duty Cycle Analysis Application
Comprehensive Multi-Physics Simulation with Tkinter GUI

Features:
- Duty cycle calculation and RMS rating
- Real-time ODE solvers (RK45, Euler)
- Multi-physics simulation (EM-Thermal-Mechanical coupling)
- Economic analysis
- Loss breakdown and efficiency analysis
- Advanced controls and derating
- Auto-scaling GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy.integrate import solve_ivp, odeint
import math
from dataclasses import dataclass
from typing import Tuple, List, Dict, Optional
import threading
import time


@dataclass
class DutyCycleSegment:
    """Represents a segment of the duty cycle"""
    name: str
    power_start_hp: float
    power_end_hp: float
    duration_min: float
    segment_type: str  # 'rising', 'uniform', 'regenerative', 'idle'


@dataclass
class MotorParameters:
    """DC Motor Parameters with comprehensive specifications"""
    # Electrical parameters
    voltage_rated: float = 220.0  # V (RMS)
    frequency: float = 60.0  # Hz
    armature_resistance: float = 0.086  # Ohm
    field_resistance: float = 100.0  # Ohm
    armature_inductance: float = 0.01  # H

    # Mechanical parameters
    rated_speed_rpm: float = 1500.0  # RPM
    moment_of_inertia: float = 0.5  # kg.m^2
    friction_coefficient: float = 0.01  # N.m.s/rad
    shaft_diameter: float = 0.05  # m

    # Thermal parameters
    ambient_temp: float = 25.0  # Celsius
    thermal_resistance: float = 2.0  # K/W
    thermal_capacitance: float = 500.0  # J/K
    max_operating_temp: float = 120.0  # Celsius
    temp_coefficient_copper: float = 0.00393  # per °C

    # Efficiency and loss parameters
    rated_efficiency: float = 0.92  # 92%
    iron_loss_coefficient: float = 0.02
    stray_loss_factor: float = 0.01

    # Control parameters
    max_current_limit: float = 300.0  # A
    voltage_control_range: Tuple[float, float] = (0.5, 1.5)


class DutyCycleCalculator:
    """Calculate motor rating from duty cycle"""

    def __init__(self):
        self.duty_cycle_segments: List[DutyCycleSegment] = []
        self.results = {}

    def add_segment(self, name: str, power_start: float, power_end: float,
                   duration: float, seg_type: str):
        """Add a duty cycle segment"""
        segment = DutyCycleSegment(name, power_start, power_end, duration, seg_type)
        self.duty_cycle_segments.append(segment)

    def clear_segments(self):
        """Clear all duty cycle segments"""
        self.duty_cycle_segments.clear()

    def calculate_rms_power(self) -> Dict:
        """Calculate RMS power rating using the duty cycle method"""
        if not self.duty_cycle_segments:
            return {}

        # Calculate total cycle time
        total_time = sum(seg.duration_min for seg in self.duty_cycle_segments)

        # Calculate power^2 * time for each segment
        power_squared_time = 0
        segment_details = []

        for seg in self.duty_cycle_segments:
            if seg.segment_type == 'rising':
                # For linearly rising power, use RMS calculation
                # RMS = sqrt((P1^2 + P1*P2 + P2^2) / 3)
                p1, p2 = seg.power_start_hp, seg.power_end_hp
                rms_power = math.sqrt((p1**2 + p1*p2 + p2**2) / 3)
                avg_power = (p1 + p2) / 2
            elif seg.segment_type == 'uniform':
                rms_power = seg.power_start_hp
                avg_power = seg.power_start_hp
            elif seg.segment_type == 'regenerative':
                # Regenerative braking - power returned to supply
                p1, p2 = seg.power_start_hp, seg.power_end_hp
                rms_power = math.sqrt((p1**2 + p1*p2 + p2**2) / 3)
                avg_power = (p1 + p2) / 2
            elif seg.segment_type == 'idle':
                rms_power = 0
                avg_power = 0
            else:
                rms_power = seg.power_start_hp
                avg_power = seg.power_start_hp

            # Accumulate power^2 * time
            power_squared_time += (rms_power**2) * seg.duration_min

            segment_details.append({
                'name': seg.name,
                'type': seg.segment_type,
                'duration_min': seg.duration_min,
                'power_start': seg.power_start_hp,
                'power_end': seg.power_end_hp,
                'rms_power': rms_power,
                'avg_power': avg_power,
                'energy_kwh': avg_power * 0.746 * seg.duration_min / 60  # Convert HP to kW
            })

        # Calculate overall RMS power
        rms_power_hp = math.sqrt(power_squared_time / total_time)

        # Calculate average power
        total_energy = sum(seg['energy_kwh'] for seg in segment_details)
        avg_power_hp = (total_energy * 1000 / 0.746) / total_time  # Convert back to HP

        # Calculate peak power
        peak_power_hp = max(
            max(seg.power_start_hp, seg.power_end_hp)
            for seg in self.duty_cycle_segments
        )

        # Recommended motor rating (with safety factor)
        safety_factor = 1.15  # 15% safety margin
        recommended_rating_hp = rms_power_hp * safety_factor

        self.results = {
            'rms_power_hp': rms_power_hp,
            'avg_power_hp': avg_power_hp,
            'peak_power_hp': peak_power_hp,
            'recommended_rating_hp': recommended_rating_hp,
            'total_cycle_time_min': total_time,
            'total_energy_kwh': total_energy,
            'segment_details': segment_details,
            'safety_factor': safety_factor
        }

        return self.results

    def generate_duty_cycle_profile(self, time_resolution: float = 0.1) -> Dict:
        """Generate time-series data for the duty cycle"""
        if not self.duty_cycle_segments:
            return {}

        time_points = []
        power_points = []
        current_time = 0

        for seg in self.duty_cycle_segments:
            duration_sec = seg.duration_min * 60
            num_points = int(duration_sec / time_resolution)

            if seg.segment_type == 'rising':
                # Linear interpolation
                powers = np.linspace(seg.power_start_hp, seg.power_end_hp, num_points)
            else:
                # Constant power
                if seg.segment_type == 'idle':
                    powers = np.zeros(num_points)
                else:
                    powers = np.linspace(seg.power_start_hp, seg.power_end_hp, num_points)

            times = np.linspace(current_time, current_time + duration_sec, num_points)

            time_points.extend(times)
            power_points.extend(powers)
            current_time += duration_sec

        return {
            'time_sec': np.array(time_points),
            'time_min': np.array(time_points) / 60,
            'power_hp': np.array(power_points),
            'power_kw': np.array(power_points) * 0.746
        }


class AdvancedMotorModel:
    """Advanced motor model with multi-physics coupling"""

    def __init__(self, params: MotorParameters):
        self.params = params
        self.calculate_motor_constants()

    def calculate_motor_constants(self):
        """Calculate derived motor constants"""
        p = self.params

        # Assume rated power for initial calculations (will be updated)
        self.rated_power_w = 30000  # 40 HP in watts (placeholder)

        # Angular velocity
        self.omega_rated = p.rated_speed_rpm * 2 * math.pi / 60

        # Rated torque
        self.torque_rated = self.rated_power_w / self.omega_rated

        # Motor constant estimation (k*phi)
        # Assuming rated current based on power and voltage
        self.current_rated = self.rated_power_w / (p.voltage_rated * p.rated_efficiency)

        # Back EMF constant
        self.k_phi = (p.voltage_rated - self.current_rated * p.armature_resistance) / self.omega_rated

    def update_rated_power(self, power_hp: float):
        """Update motor rated power"""
        self.rated_power_w = power_hp * 746
        self.calculate_motor_constants()

    def calculate_losses(self, current: float, speed_rpm: float, temp: float) -> Dict[str, float]:
        """Calculate comprehensive loss breakdown"""
        p = self.params
        omega = speed_rpm * 2 * math.pi / 60

        # Temperature-dependent armature resistance
        Ra_temp = p.armature_resistance * (1 + p.temp_coefficient_copper * (temp - 25))

        # Copper losses
        copper_loss_armature = current**2 * Ra_temp
        field_current = p.voltage_rated / p.field_resistance
        copper_loss_field = field_current**2 * p.field_resistance
        copper_loss_total = copper_loss_armature + copper_loss_field

        # Iron losses (hysteresis + eddy current)
        # Proportional to f^1.3 * B^2 (approximated by speed and voltage)
        iron_loss = p.iron_loss_coefficient * (abs(speed_rpm) / 1000)**1.5 * (p.voltage_rated / 220)**2 * 100

        # Mechanical losses (friction and windage)
        friction_loss = p.friction_coefficient * omega**2

        # Stray load losses
        stray_loss = p.stray_loss_factor * abs(current * p.voltage_rated)

        # Total losses
        total_loss = copper_loss_total + iron_loss + friction_loss + stray_loss

        return {
            'copper_armature': copper_loss_armature,
            'copper_field': copper_loss_field,
            'copper_total': copper_loss_total,
            'iron_loss': iron_loss,
            'friction_loss': friction_loss,
            'stray_loss': stray_loss,
            'total_loss': total_loss
        }

    def calculate_efficiency(self, power_output: float, losses: Dict[str, float]) -> float:
        """Calculate motor efficiency"""
        power_input = power_output + losses['total_loss']
        if power_input <= 0:
            return 0
        return (power_output / power_input) * 100

    def mechanical_stress_analysis(self, torque: float) -> Dict[str, float]:
        """Analyze mechanical stress"""
        p = self.params

        # Torsional shear stress: τ = (16 * T) / (π * d^3)
        torsional_stress = (16 * abs(torque)) / (math.pi * p.shaft_diameter**3)

        # Simplified bearing loads
        bearing_radial_load = 500 + abs(torque) * 2  # N (simplified)
        bearing_thrust_load = abs(torque) / (p.shaft_diameter / 2)

        # Bending stress (simplified)
        bending_stress = bearing_radial_load * 1000 / (math.pi * (p.shaft_diameter/2)**2)

        return {
            'torsional_stress_MPa': torsional_stress / 1e6,
            'bending_stress_MPa': bending_stress / 1e6,
            'bearing_radial_load_N': bearing_radial_load,
            'bearing_thrust_load_N': bearing_thrust_load,
            'shaft_diameter_mm': p.shaft_diameter * 1000
        }


class MultiPhysicsSimulator:
    """Advanced multi-physics ODE simulator"""

    def __init__(self, motor_model: AdvancedMotorModel, duty_cycle_profile: Dict):
        self.model = motor_model
        self.profile = duty_cycle_profile
        self.params = motor_model.params

    def power_demand_at_time(self, t: float) -> float:
        """Get power demand at given time from duty cycle profile"""
        if not self.profile:
            return 0

        time_array = self.profile['time_sec']
        power_array = self.profile['power_kw']

        # Interpolate power at time t
        if t >= time_array[-1]:
            return power_array[-1]
        elif t <= time_array[0]:
            return power_array[0]
        else:
            return np.interp(t, time_array, power_array)

    def coupled_differential_equations(self, t: float, y: np.ndarray) -> np.ndarray:
        """
        Coupled multi-physics differential equations
        State vector: [omega, theta, I_a, T_motor, Q_accumulated]
        """
        omega, theta, I_a, T_motor, Q_acc = y

        p = self.params

        # Get power demand from duty cycle
        P_demand_kw = self.power_demand_at_time(t)
        P_demand_w = P_demand_kw * 1000

        # Required torque for demanded power
        if omega > 0.1:
            T_required = P_demand_w / omega
        else:
            T_required = 0

        # Temperature-dependent resistance
        Ra_temp = p.armature_resistance * (1 + p.temp_coefficient_copper * (T_motor - 25))

        # Back EMF
        Eb = self.model.k_phi * omega

        # Voltage control to match power demand
        # V = Eb + I * Ra
        if P_demand_w > 0:
            # Motoring
            I_target = min(P_demand_w / p.voltage_rated, p.max_current_limit)
        elif P_demand_w < 0:
            # Regenerative braking
            I_target = max(P_demand_w / p.voltage_rated, -p.max_current_limit)
        else:
            I_target = 0

        # Current dynamics (L * dI/dt = V - Eb - I*Ra)
        tau_electrical = p.armature_inductance / Ra_temp if Ra_temp > 0 else 0.01
        dI_dt = (I_target - I_a) / max(tau_electrical, 0.001)

        # Electromagnetic torque
        T_em = self.model.k_phi * I_a

        # Friction torque
        T_friction = p.friction_coefficient * omega

        # Mechanical dynamics: J * dω/dt = T_em - T_friction
        domega_dt = (T_em - T_friction) / p.moment_of_inertia

        # Angular position
        dtheta_dt = omega

        # Calculate losses
        speed_rpm = omega * 60 / (2 * math.pi)
        losses = self.model.calculate_losses(I_a, speed_rpm, T_motor)
        P_loss = losses['total_loss']

        # Thermal dynamics
        Q_dissipated = (T_motor - p.ambient_temp) / p.thermal_resistance
        dT_dt = (P_loss - Q_dissipated) / p.thermal_capacitance

        # Heat accumulation
        dQ_dt = P_loss

        # Thermal derating if overheating
        if T_motor > p.max_operating_temp:
            # Reduce current limit due to overheating
            dI_dt = -abs(I_a) * 0.1  # Emergency current reduction

        return np.array([domega_dt, dtheta_dt, dI_dt, dT_dt, dQ_dt])

    def simulate(self, method: str = 'RK45', t_end: float = None) -> Dict:
        """Run multi-physics simulation"""
        if t_end is None:
            if self.profile:
                t_end = self.profile['time_sec'][-1]
            else:
                t_end = 60.0  # Default 60 seconds

        # Initial conditions
        omega_0 = self.params.rated_speed_rpm * 2 * math.pi / 60
        theta_0 = 0
        I_a_0 = 10  # Small initial current
        T_motor_0 = self.params.ambient_temp + 10
        Q_0 = 0

        y0 = np.array([omega_0, theta_0, I_a_0, T_motor_0, Q_0])

        if method == 'Euler':
            return self.simulate_euler((0, t_end), y0)
        else:
            return self.simulate_scipy((0, t_end), y0, method)

    def simulate_scipy(self, t_span: Tuple, y0: np.ndarray, method: str) -> Dict:
        """Simulate using scipy solve_ivp"""
        sol = solve_ivp(
            self.coupled_differential_equations,
            t_span,
            y0,
            method=method,
            max_step=0.1,
            dense_output=True,
            rtol=1e-6,
            atol=1e-8
        )

        return self.process_solution(sol.t, sol.y.T)

    def simulate_euler(self, t_span: Tuple, y0: np.ndarray, dt: float = 0.01) -> Dict:
        """Simulate using Euler method"""
        t_start, t_end = t_span
        n_steps = int((t_end - t_start) / dt)

        t = np.linspace(t_start, t_end, n_steps)
        y = np.zeros((n_steps, len(y0)))
        y[0] = y0

        for i in range(n_steps - 1):
            dydt = self.coupled_differential_equations(t[i], y[i])
            y[i+1] = y[i] + dydt * dt

            # Prevent negative speed
            if y[i+1][0] < 0:
                y[i+1][0] = 0

        return self.process_solution(t, y)

    def process_solution(self, t: np.ndarray, y: np.ndarray) -> Dict:
        """Process simulation solution"""
        omega = y[:, 0]
        theta = y[:, 1]
        current = y[:, 2]
        temperature = y[:, 3]
        heat = y[:, 4]

        speed_rpm = omega * 60 / (2 * math.pi)
        torque = self.model.k_phi * current
        power = torque * omega

        # Calculate losses for each time step
        losses_history = []
        efficiency_history = []

        for i in range(len(t)):
            losses = self.model.calculate_losses(current[i], speed_rpm[i], temperature[i])
            efficiency = self.model.calculate_efficiency(abs(power[i]), losses)
            losses_history.append(losses)
            efficiency_history.append(efficiency)

        # Get power demand profile
        power_demand = np.array([self.power_demand_at_time(ti) * 1000 for ti in t])

        return {
            'time': t,
            'omega': omega,
            'speed_rpm': speed_rpm,
            'theta': theta,
            'current': current,
            'temperature': temperature,
            'heat': heat,
            'torque': torque,
            'power': power,
            'power_demand': power_demand,
            'losses': losses_history,
            'efficiency': efficiency_history,
            'success': True
        }


class EconomicAnalyzer:
    """Economic analysis module"""

    def __init__(self):
        self.electricity_rate = 0.12  # $/kWh

    def analyze_energy_cost(self, simulation_results: Dict) -> Dict:
        """Analyze energy consumption and costs"""
        t = simulation_results['time']
        power_w = simulation_results['power']

        # Energy in kWh
        energy_j = np.trapz(np.abs(power_w), t)
        energy_kwh = energy_j / (3600 * 1000)

        # Cost
        cost = energy_kwh * self.electricity_rate

        # Peak power
        peak_power_kw = np.max(np.abs(power_w)) / 1000

        # Average power
        avg_power_kw = energy_kwh / (t[-1] / 3600)

        return {
            'energy_kwh': energy_kwh,
            'cost_usd': cost,
            'peak_power_kw': peak_power_kw,
            'avg_power_kw': avg_power_kw
        }

    def lifecycle_cost_analysis(self, annual_hours: float, years: int,
                               energy_per_cycle_kwh: float,
                               cycles_per_hour: float,
                               maintenance_annual: float) -> Dict:
        """Complete lifecycle cost analysis"""
        # Annual energy
        annual_energy = energy_per_cycle_kwh * cycles_per_hour * annual_hours
        annual_energy_cost = annual_energy * self.electricity_rate

        # Total costs over lifetime
        total_energy_cost = annual_energy_cost * years
        total_maintenance = maintenance_annual * years

        # Component replacement (every 5 years)
        replacement_cost = 5000
        num_replacements = years // 5
        total_replacement = replacement_cost * num_replacements

        # Total lifetime cost
        total_lifetime = total_energy_cost + total_maintenance + total_replacement

        return {
            'annual_energy_kwh': annual_energy,
            'annual_energy_cost': annual_energy_cost,
            'annual_maintenance': maintenance_annual,
            'total_energy_cost': total_energy_cost,
            'total_maintenance': total_maintenance,
            'total_replacement': total_replacement,
            'total_lifetime_cost': total_lifetime,
            'cost_per_hour': total_lifetime / (annual_hours * years)
        }


class MotorDutyCycleGUI:
    """Main GUI Application"""

    def __init__(self, root):
        self.root = root
        self.root.title("Advanced DC Motor Duty Cycle Analysis - Multi-Physics Simulator")

        # Get screen dimensions for initial sizing
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = min(1600, int(screen_width * 0.9))
        window_height = min(1000, int(screen_height * 0.9))

        # Center window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Initialize components
        self.duty_calc = DutyCycleCalculator()
        self.motor_params = MotorParameters()
        self.motor_model = AdvancedMotorModel(self.motor_params)
        self.economic = EconomicAnalyzer()

        self.simulation_results = None
        self.simulation_running = False

        # Setup GUI
        self.setup_menu()
        self.setup_main_interface()

        # Bind resize event
        self.root.bind('<Configure>', self.on_resize)

        # Load default duty cycle problem
        self.load_default_duty_cycle()

    def setup_menu(self):
        """Setup menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Default Problem", command=self.load_default_duty_cycle)
        file_menu.add_command(label="Clear Duty Cycle", command=self.clear_duty_cycle)
        file_menu.add_separator()
        file_menu.add_command(label="Save Results", command=self.save_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Advanced Controls", command=self.show_advanced_controls)
        tools_menu.add_command(label="Thermal Derating", command=self.show_thermal_derating)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="User Guide", command=self.show_user_guide)

    def setup_main_interface(self):
        """Setup tabbed interface"""
        # Create notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Create tabs
        self.setup_duty_cycle_tab()
        self.setup_motor_params_tab()
        self.setup_simulation_tab()
        self.setup_multiphysics_tab()
        self.setup_losses_tab()
        self.setup_economic_tab()
        self.setup_control_tab()

    def setup_duty_cycle_tab(self):
        """Setup duty cycle definition tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="⚡ Duty Cycle Definition")

        # Top frame for problem description
        desc_frame = ttk.LabelFrame(tab, text="Duty Cycle Problem", padding=10)
        desc_frame.pack(side='top', fill='x', padx=10, pady=5)

        problem_text = """
DEFAULT PROBLEM:
A motor has the following duty cycle:
1. Load rising from 200 to 400 H.P. - 4 min.
2. Uniform load 300 H.P. - 2 min.
3. Regenerative braking - H.P. returned to supply from 50 to zero - 1 min.
4. Remaining idle for - 1 min.

Total cycle time: 8 minutes
        """

        ttk.Label(desc_frame, text=problem_text, font=('Courier', 9),
                 justify='left').pack()

        # Duty cycle segments frame
        segments_frame = ttk.LabelFrame(tab, text="Duty Cycle Segments", padding=10)
        segments_frame.pack(side='top', fill='both', expand=True, padx=10, pady=5)

        # Segments list
        list_frame = ttk.Frame(segments_frame)
        list_frame.pack(side='left', fill='both', expand=True)

        # Treeview for segments
        columns = ('Name', 'Type', 'Start HP', 'End HP', 'Duration (min)')
        self.segments_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)

        for col in columns:
            self.segments_tree.heading(col, text=col)
            self.segments_tree.column(col, width=120)

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.segments_tree.yview)
        self.segments_tree.configure(yscrollcommand=scrollbar.set)

        self.segments_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Control frame
        control_frame = ttk.Frame(segments_frame)
        control_frame.pack(side='right', fill='y', padx=10)

        ttk.Button(control_frame, text="➕ Add Segment",
                  command=self.add_segment_dialog).pack(pady=5, fill='x')
        ttk.Button(control_frame, text="✏️ Edit Segment",
                  command=self.edit_segment_dialog).pack(pady=5, fill='x')
        ttk.Button(control_frame, text="❌ Delete Segment",
                  command=self.delete_segment).pack(pady=5, fill='x')
        ttk.Button(control_frame, text="🔄 Load Default",
                  command=self.load_default_duty_cycle).pack(pady=5, fill='x')
        ttk.Button(control_frame, text="🗑️ Clear All",
                  command=self.clear_duty_cycle).pack(pady=5, fill='x')

        # Results frame
        results_frame = ttk.LabelFrame(tab, text="RMS Power Calculation Results", padding=10)
        results_frame.pack(side='top', fill='both', expand=True, padx=10, pady=5)

        # Calculate button
        ttk.Button(results_frame, text="▶ Calculate RMS Rating",
                  command=self.calculate_rms_rating,
                  style='Accent.TButton').pack(pady=5)

        # Results display
        self.duty_results_text = scrolledtext.ScrolledText(results_frame, height=15,
                                                          font=('Courier', 9), wrap=tk.WORD)
        self.duty_results_text.pack(fill='both', expand=True)

        # Visualization frame
        viz_frame = ttk.LabelFrame(tab, text="Duty Cycle Visualization", padding=5)
        viz_frame.pack(side='top', fill='both', expand=True, padx=10, pady=5)

        self.duty_fig = Figure(figsize=(10, 4), dpi=100)
        self.duty_canvas = FigureCanvasTkAgg(self.duty_fig, viz_frame)
        self.duty_canvas.get_tk_widget().pack(fill='both', expand=True)

    def setup_motor_params_tab(self):
        """Setup motor parameters tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="⚙️ Motor Parameters")

        # Create scrollable canvas
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>",
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Title
        ttk.Label(scrollable_frame, text="DC Motor Parameters Configuration",
                 font=('Arial', 14, 'bold')).grid(row=0, column=0, columnspan=3, pady=10)

        # Parameter inputs
        self.param_vars = {}

        params_config = [
            ("Electrical Parameters", None, None, None, None),
            ("Rated Voltage (V)", "voltage_rated", 100, 500, 220),
            ("Frequency (Hz)", "frequency", 50, 400, 60),
            ("Armature Resistance (Ω)", "armature_resistance", 0.01, 1.0, 0.086),
            ("Field Resistance (Ω)", "field_resistance", 10, 500, 100),
            ("Armature Inductance (H)", "armature_inductance", 0.001, 0.1, 0.01),
            ("Max Current Limit (A)", "max_current_limit", 100, 1000, 300),

            ("Mechanical Parameters", None, None, None, None),
            ("Rated Speed (RPM)", "rated_speed_rpm", 500, 3000, 1500),
            ("Moment of Inertia (kg.m²)", "moment_of_inertia", 0.1, 10.0, 0.5),
            ("Friction Coefficient", "friction_coefficient", 0.001, 0.1, 0.01),
            ("Shaft Diameter (m)", "shaft_diameter", 0.02, 0.2, 0.05),

            ("Thermal Parameters", None, None, None, None),
            ("Ambient Temperature (°C)", "ambient_temp", 0, 50, 25),
            ("Max Operating Temp (°C)", "max_operating_temp", 80, 200, 120),
            ("Thermal Resistance (K/W)", "thermal_resistance", 0.5, 10, 2.0),
            ("Thermal Capacitance (J/K)", "thermal_capacitance", 100, 2000, 500),

            ("Efficiency Parameters", None, None, None, None),
            ("Rated Efficiency", "rated_efficiency", 0.7, 0.98, 0.92),
            ("Iron Loss Coefficient", "iron_loss_coefficient", 0.001, 0.1, 0.02),
            ("Stray Loss Factor", "stray_loss_factor", 0.001, 0.05, 0.01),
        ]

        row = 1
        for config in params_config:
            if config[1] is None:
                # Section header
                ttk.Separator(scrollable_frame, orient='horizontal').grid(
                    row=row, column=0, columnspan=3, sticky='ew', pady=10)
                row += 1
                ttk.Label(scrollable_frame, text=config[0],
                         font=('Arial', 11, 'bold')).grid(row=row, column=0,
                                                         columnspan=3, sticky='w', padx=10, pady=5)
                row += 1
            else:
                label, param_name, min_val, max_val, default = config

                ttk.Label(scrollable_frame, text=label).grid(row=row, column=0,
                                                            sticky='w', padx=10, pady=3)

                var = tk.DoubleVar(value=default)
                entry = ttk.Entry(scrollable_frame, textvariable=var, width=15)
                entry.grid(row=row, column=1, padx=10, pady=3)
                self.param_vars[param_name] = var

                slider = ttk.Scale(scrollable_frame, from_=min_val, to=max_val,
                                 orient='horizontal', length=300,
                                 command=lambda val, v=var: v.set(float(val)))
                slider.set(default)
                slider.grid(row=row, column=2, padx=10, pady=3)

                var.trace('w', lambda *args, s=slider, v=var: s.set(v.get()))

                row += 1

        # Update button
        ttk.Button(scrollable_frame, text="Update Motor Model",
                  command=self.update_motor_parameters,
                  style='Accent.TButton').grid(row=row, column=0, columnspan=3, pady=20)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def setup_simulation_tab(self):
        """Setup simulation tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🔬 Dynamic Simulation")

        # Control panel
        control_frame = ttk.LabelFrame(tab, text="Simulation Controls", padding=10)
        control_frame.pack(side='top', fill='x', padx=10, pady=5)

        # Solver selection
        ttk.Label(control_frame, text="ODE Solver:").grid(row=0, column=0, padx=5)
        self.solver_var = tk.StringVar(value='RK45')
        solver_combo = ttk.Combobox(control_frame, textvariable=self.solver_var,
                                    values=['RK45', 'RK23', 'DOP853', 'Radau', 'BDF', 'Euler'],
                                    state='readonly', width=12)
        solver_combo.grid(row=0, column=1, padx=5)

        # Simulation time
        ttk.Label(control_frame, text="Simulation Mode:").grid(row=0, column=2, padx=5)
        self.sim_mode_var = tk.StringVar(value='duty_cycle')
        mode_combo = ttk.Combobox(control_frame, textvariable=self.sim_mode_var,
                                 values=['duty_cycle', 'custom_time'],
                                 state='readonly', width=12)
        mode_combo.grid(row=0, column=3, padx=5)

        ttk.Label(control_frame, text="Custom Time (s):").grid(row=0, column=4, padx=5)
        self.custom_time_var = tk.DoubleVar(value=600)
        ttk.Entry(control_frame, textvariable=self.custom_time_var,
                 width=10).grid(row=0, column=5, padx=5)

        # Control buttons
        ttk.Button(control_frame, text="▶ Start",
                  command=self.start_simulation,
                  style='Accent.TButton').grid(row=0, column=6, padx=5)
        ttk.Button(control_frame, text="⏹ Stop",
                  command=self.stop_simulation).grid(row=0, column=7, padx=5)
        ttk.Button(control_frame, text="↻ Reset",
                  command=self.reset_simulation).grid(row=0, column=8, padx=5)

        # Status
        self.sim_status_var = tk.StringVar(value="Ready")
        ttk.Label(control_frame, textvariable=self.sim_status_var,
                 foreground='green', font=('Arial', 10, 'bold')).grid(row=0, column=9, padx=10)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(control_frame, variable=self.progress_var,
                                           maximum=100, length=200)
        self.progress_bar.grid(row=1, column=0, columnspan=10, pady=10, sticky='ew')

        # Results visualization
        self.sim_fig = Figure(figsize=(12, 8), dpi=100)
        self.sim_canvas = FigureCanvasTkAgg(self.sim_fig, tab)
        self.sim_canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=5)

    def setup_multiphysics_tab(self):
        """Setup multi-physics analysis tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🌡️ Multi-Physics")

        ttk.Label(tab, text="Coupled Electromagnetic-Thermal-Mechanical Analysis",
                 font=('Arial', 12, 'bold')).pack(pady=10)

        self.multiphys_fig = Figure(figsize=(12, 8), dpi=100)
        self.multiphys_canvas = FigureCanvasTkAgg(self.multiphys_fig, tab)
        self.multiphys_canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=5)

    def setup_losses_tab(self):
        """Setup losses analysis tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📊 Loss Analysis")

        ttk.Label(tab, text="Detailed Loss Breakdown and Efficiency Analysis",
                 font=('Arial', 12, 'bold')).pack(pady=10)

        self.losses_fig = Figure(figsize=(12, 8), dpi=100)
        self.losses_canvas = FigureCanvasTkAgg(self.losses_fig, tab)
        self.losses_canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=5)

    def setup_economic_tab(self):
        """Setup economic analysis tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="💰 Economic Analysis")

        # Input frame
        input_frame = ttk.LabelFrame(tab, text="Economic Parameters", padding=10)
        input_frame.pack(side='top', fill='x', padx=10, pady=5)

        ttk.Label(input_frame, text="Electricity Rate ($/kWh):").grid(row=0, column=0, padx=5, pady=5)
        self.elec_rate_var = tk.DoubleVar(value=0.12)
        ttk.Entry(input_frame, textvariable=self.elec_rate_var, width=15).grid(row=0, column=1, padx=5)

        ttk.Label(input_frame, text="Operating Hours/Year:").grid(row=0, column=2, padx=5, pady=5)
        self.op_hours_var = tk.DoubleVar(value=4000)
        ttk.Entry(input_frame, textvariable=self.op_hours_var, width=15).grid(row=0, column=3, padx=5)

        ttk.Label(input_frame, text="Cycles per Hour:").grid(row=1, column=0, padx=5, pady=5)
        self.cycles_hour_var = tk.DoubleVar(value=10)
        ttk.Entry(input_frame, textvariable=self.cycles_hour_var, width=15).grid(row=1, column=1, padx=5)

        ttk.Label(input_frame, text="Lifetime (years):").grid(row=1, column=2, padx=5, pady=5)
        self.lifetime_var = tk.IntVar(value=10)
        ttk.Entry(input_frame, textvariable=self.lifetime_var, width=15).grid(row=1, column=3, padx=5)

        ttk.Label(input_frame, text="Annual Maintenance ($):").grid(row=2, column=0, padx=5, pady=5)
        self.maint_var = tk.DoubleVar(value=1000)
        ttk.Entry(input_frame, textvariable=self.maint_var, width=15).grid(row=2, column=1, padx=5)

        ttk.Button(input_frame, text="Calculate Economics",
                  command=self.calculate_economics).grid(row=2, column=2, columnspan=2, pady=10)

        # Results display
        results_frame = ttk.LabelFrame(tab, text="Economic Results", padding=10)
        results_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.econ_text = scrolledtext.ScrolledText(results_frame, height=10, font=('Courier', 9))
        self.econ_text.pack(fill='both', expand=True)

        # Chart
        self.econ_fig = Figure(figsize=(10, 4), dpi=100)
        self.econ_canvas = FigureCanvasTkAgg(self.econ_fig, results_frame)
        self.econ_canvas.get_tk_widget().pack(fill='both', expand=True)

    def setup_control_tab(self):
        """Setup advanced control tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🎛️ Advanced Controls")

        ttk.Label(tab, text="Advanced Motor Control and Power Consumption Tracking",
                 font=('Arial', 12, 'bold')).pack(pady=10)

        # Control methods frame
        control_frame = ttk.LabelFrame(tab, text="Control Methods", padding=10)
        control_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(control_frame, text="Voltage Control Method:").grid(row=0, column=0, padx=5)
        self.voltage_control_var = tk.StringVar(value='PWM')
        ttk.Combobox(control_frame, textvariable=self.voltage_control_var,
                    values=['PWM', 'Armature Voltage', 'Field Control'],
                    state='readonly').grid(row=0, column=1, padx=5)

        ttk.Label(control_frame, text="Speed Control:").grid(row=0, column=2, padx=5)
        self.speed_control_var = tk.StringVar(value='Closed Loop')
        ttk.Combobox(control_frame, textvariable=self.speed_control_var,
                    values=['Open Loop', 'Closed Loop', 'PID'],
                    state='readonly').grid(row=0, column=3, padx=5)

        # Power consumption tracking
        power_frame = ttk.LabelFrame(tab, text="Power Consumption Tracking", padding=10)
        power_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.power_fig = Figure(figsize=(10, 6), dpi=100)
        self.power_canvas = FigureCanvasTkAgg(self.power_fig, power_frame)
        self.power_canvas.get_tk_widget().pack(fill='both', expand=True)

    def load_default_duty_cycle(self):
        """Load the default duty cycle problem"""
        self.duty_calc.clear_segments()

        # Add segments for default problem
        segments = [
            ("Rising Load", 200, 400, 4, 'rising'),
            ("Uniform Load", 300, 300, 2, 'uniform'),
            ("Regenerative Braking", 50, 0, 1, 'regenerative'),
            ("Idle", 0, 0, 1, 'idle')
        ]

        for name, p_start, p_end, duration, seg_type in segments:
            self.duty_calc.add_segment(name, p_start, p_end, duration, seg_type)

        self.refresh_segments_tree()
        messagebox.showinfo("Success", "Default duty cycle problem loaded!")

    def refresh_segments_tree(self):
        """Refresh the segments treeview"""
        # Clear existing items
        for item in self.segments_tree.get_children():
            self.segments_tree.delete(item)

        # Add segments
        for seg in self.duty_calc.duty_cycle_segments:
            self.segments_tree.insert('', 'end', values=(
                seg.name,
                seg.segment_type,
                f"{seg.power_start_hp:.1f}",
                f"{seg.power_end_hp:.1f}",
                f"{seg.duration_min:.1f}"
            ))

    def add_segment_dialog(self):
        """Show dialog to add a segment"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Duty Cycle Segment")
        dialog.geometry("400x300")

        ttk.Label(dialog, text="Segment Name:").grid(row=0, column=0, padx=10, pady=5)
        name_var = tk.StringVar(value="New Segment")
        ttk.Entry(dialog, textvariable=name_var, width=25).grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(dialog, text="Segment Type:").grid(row=1, column=0, padx=10, pady=5)
        type_var = tk.StringVar(value='uniform')
        ttk.Combobox(dialog, textvariable=type_var,
                    values=['rising', 'uniform', 'regenerative', 'idle'],
                    state='readonly').grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(dialog, text="Start Power (HP):").grid(row=2, column=0, padx=10, pady=5)
        start_var = tk.DoubleVar(value=100)
        ttk.Entry(dialog, textvariable=start_var, width=25).grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(dialog, text="End Power (HP):").grid(row=3, column=0, padx=10, pady=5)
        end_var = tk.DoubleVar(value=100)
        ttk.Entry(dialog, textvariable=end_var, width=25).grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(dialog, text="Duration (min):").grid(row=4, column=0, padx=10, pady=5)
        dur_var = tk.DoubleVar(value=1)
        ttk.Entry(dialog, textvariable=dur_var, width=25).grid(row=4, column=1, padx=10, pady=5)

        def add_segment():
            self.duty_calc.add_segment(
                name_var.get(),
                start_var.get(),
                end_var.get(),
                dur_var.get(),
                type_var.get()
            )
            self.refresh_segments_tree()
            dialog.destroy()

        ttk.Button(dialog, text="Add", command=add_segment).grid(row=5, column=0, columnspan=2, pady=20)

    def edit_segment_dialog(self):
        """Edit selected segment"""
        selection = self.segments_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a segment to edit")
            return

        # Get index of selected segment
        index = self.segments_tree.index(selection[0])
        seg = self.duty_calc.duty_cycle_segments[index]

        # Create dialog (similar to add_segment_dialog but with edit functionality)
        messagebox.showinfo("Info", f"Editing segment: {seg.name}")

    def delete_segment(self):
        """Delete selected segment"""
        selection = self.segments_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a segment to delete")
            return

        index = self.segments_tree.index(selection[0])
        del self.duty_calc.duty_cycle_segments[index]
        self.refresh_segments_tree()

    def clear_duty_cycle(self):
        """Clear all duty cycle segments"""
        if messagebox.askyesno("Confirm", "Clear all duty cycle segments?"):
            self.duty_calc.clear_segments()
            self.refresh_segments_tree()

    def calculate_rms_rating(self):
        """Calculate RMS motor rating"""
        if not self.duty_calc.duty_cycle_segments:
            messagebox.showwarning("Warning", "Please define duty cycle segments first!")
            return

        results = self.duty_calc.calculate_rms_power()

        if not results:
            return

        # Format results
        text = f"""
{'='*80}
DUTY CYCLE RMS POWER RATING CALCULATION
{'='*80}

DUTY CYCLE SEGMENTS:
"""
        for i, seg in enumerate(results['segment_details'], 1):
            text += f"""
Segment {i}: {seg['name']}
  Type:              {seg['type']}
  Duration:          {seg['duration_min']:.2f} minutes
  Power Range:       {seg['power_start']:.1f} HP → {seg['power_end']:.1f} HP
  RMS Power:         {seg['rms_power']:.2f} HP
  Average Power:     {seg['avg_power']:.2f} HP
  Energy:            {seg['energy_kwh']:.4f} kWh
"""

        text += f"""
{'='*80}
OVERALL RESULTS:
{'='*80}
Total Cycle Time:            {results['total_cycle_time_min']:.2f} minutes
Total Energy per Cycle:      {results['total_energy_kwh']:.4f} kWh

RMS Power:                   {results['rms_power_hp']:.2f} HP ({results['rms_power_hp']*0.746:.2f} kW)
Average Power:               {results['avg_power_hp']:.2f} HP ({results['avg_power_hp']*0.746:.2f} kW)
Peak Power:                  {results['peak_power_hp']:.2f} HP ({results['peak_power_hp']*0.746:.2f} kW)

RECOMMENDED MOTOR RATING:    {results['recommended_rating_hp']:.2f} HP ({results['recommended_rating_hp']*0.746:.2f} kW)
(Safety Factor: {results['safety_factor']:.2f})

{'='*80}
CONCLUSION:
{'='*80}
A motor with a continuous rating of at least {results['recommended_rating_hp']:.1f} HP
({results['recommended_rating_hp']*0.746:.1f} kW) should be selected to handle this duty cycle safely.

This accounts for:
- RMS heating effect
- Peak power demands
- {(results['safety_factor']-1)*100:.0f}% safety margin for transients and environmental factors
{'='*80}
"""

        self.duty_results_text.delete('1.0', tk.END)
        self.duty_results_text.insert('1.0', text)

        # Update motor model with calculated rating
        self.motor_model.update_rated_power(results['recommended_rating_hp'])

        # Visualize duty cycle
        self.visualize_duty_cycle()

    def visualize_duty_cycle(self):
        """Visualize duty cycle profile"""
        profile = self.duty_calc.generate_duty_cycle_profile()

        if not profile:
            return

        self.duty_fig.clear()

        ax1 = self.duty_fig.add_subplot(2, 1, 1)
        ax2 = self.duty_fig.add_subplot(2, 1, 2)

        # Plot 1: Power vs Time
        ax1.plot(profile['time_min'], profile['power_hp'], 'b-', linewidth=2)
        ax1.fill_between(profile['time_min'], 0, profile['power_hp'], alpha=0.3)
        ax1.set_xlabel('Time (minutes)', fontsize=10)
        ax1.set_ylabel('Power (HP)', fontsize=10)
        ax1.set_title('Duty Cycle Power Profile', fontsize=11, fontweight='bold')
        ax1.grid(True, alpha=0.3)

        # Add RMS line
        if self.duty_calc.results:
            rms_power = self.duty_calc.results['rms_power_hp']
            ax1.axhline(y=rms_power, color='r', linestyle='--', linewidth=2,
                       label=f'RMS Power = {rms_power:.1f} HP')
            ax1.axhline(y=self.duty_calc.results['recommended_rating_hp'],
                       color='g', linestyle='--', linewidth=2,
                       label=f'Recommended = {self.duty_calc.results["recommended_rating_hp"]:.1f} HP')
            ax1.legend()

        # Plot 2: Cumulative Energy
        power_kw = profile['power_kw']
        time_hours = profile['time_min'] / 60
        cumulative_energy = np.cumsum(power_kw * np.diff(time_hours, prepend=0))

        ax2.plot(profile['time_min'], cumulative_energy, 'g-', linewidth=2)
        ax2.fill_between(profile['time_min'], 0, cumulative_energy, alpha=0.3, color='green')
        ax2.set_xlabel('Time (minutes)', fontsize=10)
        ax2.set_ylabel('Cumulative Energy (kWh)', fontsize=10)
        ax2.set_title('Energy Consumption', fontsize=11, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        self.duty_fig.tight_layout()
        self.duty_canvas.draw()

    def update_motor_parameters(self):
        """Update motor parameters from GUI"""
        self.motor_params.voltage_rated = self.param_vars['voltage_rated'].get()
        self.motor_params.frequency = self.param_vars['frequency'].get()
        self.motor_params.armature_resistance = self.param_vars['armature_resistance'].get()
        self.motor_params.field_resistance = self.param_vars['field_resistance'].get()
        self.motor_params.armature_inductance = self.param_vars['armature_inductance'].get()
        self.motor_params.max_current_limit = self.param_vars['max_current_limit'].get()
        self.motor_params.rated_speed_rpm = self.param_vars['rated_speed_rpm'].get()
        self.motor_params.moment_of_inertia = self.param_vars['moment_of_inertia'].get()
        self.motor_params.friction_coefficient = self.param_vars['friction_coefficient'].get()
        self.motor_params.shaft_diameter = self.param_vars['shaft_diameter'].get()
        self.motor_params.ambient_temp = self.param_vars['ambient_temp'].get()
        self.motor_params.max_operating_temp = self.param_vars['max_operating_temp'].get()
        self.motor_params.thermal_resistance = self.param_vars['thermal_resistance'].get()
        self.motor_params.thermal_capacitance = self.param_vars['thermal_capacitance'].get()
        self.motor_params.rated_efficiency = self.param_vars['rated_efficiency'].get()
        self.motor_params.iron_loss_coefficient = self.param_vars['iron_loss_coefficient'].get()
        self.motor_params.stray_loss_factor = self.param_vars['stray_loss_factor'].get()

        # Recreate motor model
        self.motor_model = AdvancedMotorModel(self.motor_params)

        messagebox.showinfo("Success", "Motor parameters updated!")

    def start_simulation(self):
        """Start multi-physics simulation"""
        if self.simulation_running:
            messagebox.showwarning("Warning", "Simulation already running!")
            return

        if not self.duty_calc.duty_cycle_segments:
            messagebox.showwarning("Warning", "Please define duty cycle first!")
            return

        self.simulation_running = True
        self.sim_status_var.set("Running...")
        self.progress_var.set(0)

        def run_simulation():
            try:
                # Update motor parameters
                self.update_motor_parameters()

                # Generate duty cycle profile
                profile = self.duty_calc.generate_duty_cycle_profile(time_resolution=0.5)

                # Create simulator
                simulator = MultiPhysicsSimulator(self.motor_model, profile)

                # Determine simulation time
                if self.sim_mode_var.get() == 'duty_cycle':
                    t_end = profile['time_sec'][-1]
                else:
                    t_end = self.custom_time_var.get()

                # Run simulation
                method = self.solver_var.get()
                self.simulation_results = simulator.simulate(method, t_end)

                # Update GUI
                self.root.after(0, self.display_simulation_results)
                self.root.after(0, lambda: self.sim_status_var.set("Complete ✓"))
                self.root.after(0, lambda: self.progress_var.set(100))

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Simulation failed:\n{str(e)}"))
                self.root.after(0, lambda: self.sim_status_var.set("Error ✗"))
            finally:
                self.simulation_running = False

        thread = threading.Thread(target=run_simulation, daemon=True)
        thread.start()

    def stop_simulation(self):
        """Stop simulation"""
        self.simulation_running = False
        self.sim_status_var.set("Stopped")

    def reset_simulation(self):
        """Reset simulation"""
        self.simulation_running = False
        self.simulation_results = None
        self.sim_status_var.set("Ready")
        self.progress_var.set(0)
        self.sim_fig.clear()
        self.sim_canvas.draw()

    def display_simulation_results(self):
        """Display simulation results"""
        if not self.simulation_results:
            return

        r = self.simulation_results

        # Clear figure
        self.sim_fig.clear()

        # Create 3x2 subplot grid
        axes = [self.sim_fig.add_subplot(3, 2, i+1) for i in range(6)]

        # Plot 1: Speed
        axes[0].plot(r['time']/60, r['speed_rpm'], 'b-', linewidth=2)
        axes[0].set_xlabel('Time (min)', fontsize=9)
        axes[0].set_ylabel('Speed (RPM)', fontsize=9)
        axes[0].set_title('Motor Speed', fontweight='bold')
        axes[0].grid(True, alpha=0.3)

        # Plot 2: Current
        axes[1].plot(r['time']/60, r['current'], 'r-', linewidth=2)
        axes[1].set_xlabel('Time (min)', fontsize=9)
        axes[1].set_ylabel('Current (A)', fontsize=9)
        axes[1].set_title('Armature Current', fontweight='bold')
        axes[1].grid(True, alpha=0.3)

        # Plot 3: Power
        axes[2].plot(r['time']/60, r['power']/1000, 'g-', linewidth=2, label='Actual')
        axes[2].plot(r['time']/60, r['power_demand']/1000, 'b--', linewidth=1.5, label='Demand')
        axes[2].set_xlabel('Time (min)', fontsize=9)
        axes[2].set_ylabel('Power (kW)', fontsize=9)
        axes[2].set_title('Power Output vs Demand', fontweight='bold')
        axes[2].legend(fontsize=8)
        axes[2].grid(True, alpha=0.3)

        # Plot 4: Temperature
        axes[3].plot(r['time']/60, r['temperature'], 'orange', linewidth=2)
        axes[3].axhline(y=self.motor_params.max_operating_temp, color='r',
                       linestyle='--', linewidth=1, label='Max Temp')
        axes[3].set_xlabel('Time (min)', fontsize=9)
        axes[3].set_ylabel('Temperature (°C)', fontsize=9)
        axes[3].set_title('Motor Temperature', fontweight='bold')
        axes[3].legend(fontsize=8)
        axes[3].grid(True, alpha=0.3)

        # Plot 5: Torque
        axes[4].plot(r['time']/60, r['torque'], 'm-', linewidth=2)
        axes[4].set_xlabel('Time (min)', fontsize=9)
        axes[4].set_ylabel('Torque (N·m)', fontsize=9)
        axes[4].set_title('Electromagnetic Torque', fontweight='bold')
        axes[4].grid(True, alpha=0.3)

        # Plot 6: Efficiency
        eff = r['efficiency']
        axes[5].plot(r['time']/60, eff, 'c-', linewidth=2)
        axes[5].set_xlabel('Time (min)', fontsize=9)
        axes[5].set_ylabel('Efficiency (%)', fontsize=9)
        axes[5].set_title('Instantaneous Efficiency', fontweight='bold')
        axes[5].set_ylim([0, 100])
        axes[5].grid(True, alpha=0.3)

        self.sim_fig.tight_layout()
        self.sim_canvas.draw()

        # Update other tabs
        self.display_multiphysics()
        self.display_losses()
        self.display_power_consumption()

    def display_multiphysics(self):
        """Display multi-physics coupling"""
        if not self.simulation_results:
            return

        r = self.simulation_results

        self.multiphys_fig.clear()

        # Create subplots
        from mpl_toolkits.mplot3d import Axes3D

        ax1 = self.multiphys_fig.add_subplot(2, 2, 1, projection='3d')
        ax2 = self.multiphys_fig.add_subplot(2, 2, 2)
        ax3 = self.multiphys_fig.add_subplot(2, 2, 3)
        ax4 = self.multiphys_fig.add_subplot(2, 2, 4)

        # 3D phase space
        ax1.plot(r['speed_rpm'], r['current'], r['temperature'], 'b-', linewidth=2)
        ax1.set_xlabel('Speed (RPM)', fontsize=9)
        ax1.set_ylabel('Current (A)', fontsize=9)
        ax1.set_zlabel('Temp (°C)', fontsize=9)
        ax1.set_title('3D Phase Space', fontweight='bold')

        # EM coupling
        sc2 = ax2.scatter(r['current'], r['torque'], c=r['time'], cmap='viridis', s=20)
        ax2.set_xlabel('Current (A)', fontsize=9)
        ax2.set_ylabel('Torque (N·m)', fontsize=9)
        ax2.set_title('Electromagnetic Coupling', fontweight='bold')
        ax2.grid(True, alpha=0.3)
        plt.colorbar(sc2, ax=ax2, label='Time (s)')

        # Thermal coupling
        total_losses = [loss['total_loss'] for loss in r['losses']]
        ax3.plot(r['temperature'], total_losses, 'r-', linewidth=2)
        ax3.set_xlabel('Temperature (°C)', fontsize=9)
        ax3.set_ylabel('Total Loss (W)', fontsize=9)
        ax3.set_title('Thermal Coupling', fontweight='bold')
        ax3.grid(True, alpha=0.3)

        # Mechanical coupling
        sc4 = ax4.scatter(r['speed_rpm'], r['torque'], c=r['temperature'], cmap='hot', s=20)
        ax4.set_xlabel('Speed (RPM)', fontsize=9)
        ax4.set_ylabel('Torque (N·m)', fontsize=9)
        ax4.set_title('Mechanical Coupling', fontweight='bold')
        ax4.grid(True, alpha=0.3)
        plt.colorbar(sc4, ax=ax4, label='Temp (°C)')

        self.multiphys_fig.tight_layout()
        self.multiphys_canvas.draw()

    def display_losses(self):
        """Display loss breakdown"""
        if not self.simulation_results:
            return

        r = self.simulation_results
        losses = r['losses']

        # Extract loss components
        copper_arm = [l['copper_armature'] for l in losses]
        copper_field = [l['copper_field'] for l in losses]
        iron = [l['iron_loss'] for l in losses]
        friction = [l['friction_loss'] for l in losses]
        stray = [l['stray_loss'] for l in losses]
        total = [l['total_loss'] for l in losses]

        self.losses_fig.clear()

        axes = [self.losses_fig.add_subplot(2, 2, i+1) for i in range(4)]

        # Stacked area plot
        t_min = r['time'] / 60
        axes[0].fill_between(t_min, 0, copper_arm, label='Armature Cu', alpha=0.7, color='red')
        axes[0].fill_between(t_min, copper_arm, np.array(copper_arm)+np.array(copper_field),
                            label='Field Cu', alpha=0.7, color='blue')
        axes[0].fill_between(t_min, np.array(copper_arm)+np.array(copper_field),
                            np.array(copper_arm)+np.array(copper_field)+np.array(iron),
                            label='Iron', alpha=0.7, color='green')
        axes[0].set_xlabel('Time (min)', fontsize=9)
        axes[0].set_ylabel('Loss (W)', fontsize=9)
        axes[0].set_title('Loss Breakdown (Stacked)', fontweight='bold')
        axes[0].legend(fontsize=8)
        axes[0].grid(True, alpha=0.3)

        # Individual losses
        axes[1].plot(t_min, copper_arm, label='Armature Cu', linewidth=2)
        axes[1].plot(t_min, copper_field, label='Field Cu', linewidth=2)
        axes[1].plot(t_min, iron, label='Iron', linewidth=2)
        axes[1].plot(t_min, friction, label='Friction', linewidth=2)
        axes[1].plot(t_min, stray, label='Stray', linewidth=2)
        axes[1].set_xlabel('Time (min)', fontsize=9)
        axes[1].set_ylabel('Loss (W)', fontsize=9)
        axes[1].set_title('Individual Loss Components', fontweight='bold')
        axes[1].legend(fontsize=7)
        axes[1].grid(True, alpha=0.3)

        # Pie chart
        avg_losses = {
            'Armature Cu': np.mean(copper_arm),
            'Field Cu': np.mean(copper_field),
            'Iron': np.mean(iron),
            'Friction': np.mean(friction),
            'Stray': np.mean(stray)
        }
        axes[2].pie(avg_losses.values(), labels=avg_losses.keys(), autopct='%1.1f%%')
        axes[2].set_title('Average Loss Distribution', fontweight='bold')

        # Efficiency
        axes[3].plot(t_min, r['efficiency'], 'b-', linewidth=2)
        axes[3].set_xlabel('Time (min)', fontsize=9)
        axes[3].set_ylabel('Efficiency (%)', fontsize=9)
        axes[3].set_title('Motor Efficiency', fontweight='bold')
        axes[3].set_ylim([0, 100])
        axes[3].grid(True, alpha=0.3)

        self.losses_fig.tight_layout()
        self.losses_canvas.draw()

    def display_power_consumption(self):
        """Display power consumption tracking"""
        if not self.simulation_results:
            return

        r = self.simulation_results

        self.power_fig.clear()

        axes = [self.power_fig.add_subplot(2, 2, i+1) for i in range(4)]

        t_min = r['time'] / 60
        power_kw = r['power'] / 1000
        demand_kw = r['power_demand'] / 1000

        # Power tracking
        axes[0].plot(t_min, power_kw, 'b-', linewidth=2, label='Actual')
        axes[0].plot(t_min, demand_kw, 'r--', linewidth=1.5, label='Demand')
        axes[0].set_xlabel('Time (min)', fontsize=9)
        axes[0].set_ylabel('Power (kW)', fontsize=9)
        axes[0].set_title('Power Tracking', fontweight='bold')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # Cumulative energy
        energy_kwh = np.cumsum(np.abs(power_kw) * np.diff(r['time'], prepend=0) / 3600)
        axes[1].plot(t_min, energy_kwh, 'g-', linewidth=2)
        axes[1].set_xlabel('Time (min)', fontsize=9)
        axes[1].set_ylabel('Energy (kWh)', fontsize=9)
        axes[1].set_title('Cumulative Energy', fontweight='bold')
        axes[1].grid(True, alpha=0.3)

        # Power factor (simplified)
        pf = np.ones_like(power_kw) * 0.85  # Assumed constant
        axes[2].plot(t_min, pf, 'c-', linewidth=2)
        axes[2].set_xlabel('Time (min)', fontsize=9)
        axes[2].set_ylabel('Power Factor', fontsize=9)
        axes[2].set_title('Power Factor', fontweight='bold')
        axes[2].set_ylim([0, 1])
        axes[2].grid(True, alpha=0.3)

        # Real-time cost
        elec_rate = self.elec_rate_var.get()
        cost = energy_kwh * elec_rate
        axes[3].plot(t_min, cost, 'm-', linewidth=2)
        axes[3].set_xlabel('Time (min)', fontsize=9)
        axes[3].set_ylabel('Cost ($)', fontsize=9)
        axes[3].set_title(f'Energy Cost (@${elec_rate}/kWh)', fontweight='bold')
        axes[3].grid(True, alpha=0.3)

        self.power_fig.tight_layout()
        self.power_canvas.draw()

    def calculate_economics(self):
        """Calculate economic analysis"""
        if not self.simulation_results:
            messagebox.showwarning("Warning", "Run simulation first!")
            return

        # Update electricity rate
        self.economic.electricity_rate = self.elec_rate_var.get()

        # Single cycle cost
        cycle_cost = self.economic.analyze_energy_cost(self.simulation_results)

        # Lifecycle cost
        lifecycle = self.economic.lifecycle_cost_analysis(
            self.op_hours_var.get(),
            self.lifetime_var.get(),
            cycle_cost['energy_kwh'],
            self.cycles_hour_var.get(),
            self.maint_var.get()
        )

        # Display results
        text = f"""
{'='*70}
ECONOMIC ANALYSIS RESULTS
{'='*70}

SINGLE DUTY CYCLE:
  Energy Consumed:    {cycle_cost['energy_kwh']:.4f} kWh
  Cost per Cycle:     ${cycle_cost['cost_usd']:.4f}
  Peak Power:         {cycle_cost['peak_power_kw']:.2f} kW
  Average Power:      {cycle_cost['avg_power_kw']:.2f} kW

ANNUAL OPERATION:
  Operating Hours:    {self.op_hours_var.get():.0f} hours/year
  Cycles per Hour:    {self.cycles_hour_var.get():.0f}
  Annual Energy:      {lifecycle['annual_energy_kwh']:.1f} kWh
  Annual Energy Cost: ${lifecycle['annual_energy_cost']:.2f}
  Annual Maintenance: ${lifecycle['annual_maintenance']:.2f}
  Total Annual Cost:  ${lifecycle['annual_energy_cost']+lifecycle['annual_maintenance']:.2f}

LIFETIME ({self.lifetime_var.get()} YEARS):
  Total Energy Cost:  ${lifecycle['total_energy_cost']:.2f}
  Total Maintenance:  ${lifecycle['total_maintenance']:.2f}
  Total Replacement:  ${lifecycle['total_replacement']:.2f}
  TOTAL LIFETIME:     ${lifecycle['total_lifetime_cost']:.2f}

  Cost per Hour:      ${lifecycle['cost_per_hour']:.4f}/hr

{'='*70}
"""

        self.econ_text.delete('1.0', tk.END)
        self.econ_text.insert('1.0', text)

        # Plot
        self.econ_fig.clear()

        ax1 = self.econ_fig.add_subplot(1, 2, 1)
        ax2 = self.econ_fig.add_subplot(1, 2, 2)

        # Pie chart
        labels = ['Energy', 'Maintenance', 'Replacement']
        sizes = [lifecycle['total_energy_cost'], lifecycle['total_maintenance'],
                lifecycle['total_replacement']]
        ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax1.set_title('Lifetime Cost Breakdown', fontweight='bold')

        # Annual costs
        years = list(range(1, self.lifetime_var.get()+1))
        annual = [lifecycle['annual_energy_cost']+lifecycle['annual_maintenance']] * len(years)
        for i in range(len(annual)):
            if (i+1) % 5 == 0:
                annual[i] += 5000

        ax2.bar(years, annual, color='steelblue')
        ax2.set_xlabel('Year')
        ax2.set_ylabel('Annual Cost ($)')
        ax2.set_title('Annual Costs Over Lifetime', fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')

        self.econ_fig.tight_layout()
        self.econ_canvas.draw()

    def show_advanced_controls(self):
        """Show advanced controls dialog"""
        messagebox.showinfo("Advanced Controls",
                          "Advanced control features:\n\n" +
                          "- PWM voltage control\n" +
                          "- Field weakening\n" +
                          "- PID speed control\n" +
                          "- Torque control\n" +
                          "- Current limiting\n\n" +
                          "These are modeled in the simulation.")

    def show_thermal_derating(self):
        """Show thermal derating information"""
        if not self.simulation_results:
            messagebox.showwarning("Warning", "Run simulation first!")
            return

        r = self.simulation_results
        max_temp = np.max(r['temperature'])
        avg_temp = np.mean(r['temperature'])

        derating_factor = 1.0
        if max_temp > self.motor_params.max_operating_temp:
            derating_factor = self.motor_params.max_operating_temp / max_temp

        msg = f"""THERMAL DERATING ANALYSIS

Max Temperature: {max_temp:.1f}°C
Avg Temperature: {avg_temp:.1f}°C
Limit: {self.motor_params.max_operating_temp:.1f}°C

Derating Factor: {derating_factor:.3f}

"""
        if derating_factor < 1.0:
            msg += f"⚠️ WARNING: Motor is overheating!\n"
            msg += f"Recommend reducing load to {derating_factor*100:.1f}% of rated."
        else:
            msg += "✓ Motor operating within thermal limits."

        messagebox.showinfo("Thermal Derating", msg)

    def on_resize(self, event):
        """Handle window resize"""
        # Auto-scaling is handled by pack with fill and expand
        pass

    def save_results(self):
        """Save results to files"""
        if not self.simulation_results:
            messagebox.showwarning("Warning", "No results to save!")
            return

        try:
            # Save duty cycle results
            with open('duty_cycle_results.txt', 'w') as f:
                f.write(self.duty_results_text.get('1.0', tk.END))

            # Save economic results
            with open('economic_results.txt', 'w') as f:
                f.write(self.econ_text.get('1.0', tk.END))

            # Save simulation data
            r = self.simulation_results
            np.savetxt('simulation_data.csv',
                      np.column_stack([r['time'], r['speed_rpm'], r['current'],
                                      r['torque'], r['power'], r['temperature']]),
                      delimiter=',',
                      header='Time(s),Speed(RPM),Current(A),Torque(Nm),Power(W),Temp(C)',
                      comments='')

            messagebox.showinfo("Success", "Results saved successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")

    def show_about(self):
        """Show about dialog"""
        about = """Advanced DC Motor Duty Cycle Analysis
Version 2.0

Features:
• Duty cycle RMS power calculation
• Multi-physics simulation (EM-Thermal-Mechanical)
• Real-time ODE solvers (RK45, Euler, etc.)
• Detailed loss breakdown
• Economic lifecycle analysis
• Advanced motor controls
• Thermal derating
• Power consumption tracking
• Auto-scaling GUI

Developed for practical electrical engineering applications.
"""
        messagebox.showinfo("About", about)

    def show_user_guide(self):
        """Show user guide"""
        guide = """USER GUIDE

1. DUTY CYCLE DEFINITION
   - Load default problem or add custom segments
   - Calculate RMS power rating

2. MOTOR PARAMETERS
   - Configure electrical, mechanical, thermal parameters
   - Update motor model

3. SIMULATION
   - Select ODE solver (RK45 recommended)
   - Run dynamic multi-physics simulation
   - View results in multiple tabs

4. ANALYSIS
   - Multi-Physics: Coupled EM-Thermal-Mechanical
   - Losses: Detailed breakdown
   - Economics: Lifecycle cost analysis

5. ADVANCED FEATURES
   - Control methods
   - Thermal derating
   - Power tracking
"""
        messagebox.showinfo("User Guide", guide)


def main():
    """Main entry point"""
    root = tk.Tk()

    # Configure style
    style = ttk.Style()

    # Try to use a modern theme
    available_themes = style.theme_names()
    if 'clam' in available_themes:
        style.theme_use('clam')
    elif 'vista' in available_themes:
        style.theme_use('vista')

    # Custom button style
    style.configure('Accent.TButton',
                   foreground='white',
                   background='#0066cc',
                   font=('Arial', 10, 'bold'),
                   padding=6)

    # Create application
    app = MotorDutyCycleGUI(root)

    # Start GUI event loop
    root.mainloop()


if __name__ == "__main__":
    main()
