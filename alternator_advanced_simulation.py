"""
Advanced Alternator Simulation with Multi-Physics Modeling
Includes: Electromagnetic, Thermal, Mechanical, and Economic Analysis
"""

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy.integrate import solve_ivp, odeint
import threading
import time
from datetime import datetime

class AlternatorSimulation:
    """Advanced Alternator Simulation with Multi-Physics Modeling"""

    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Alternator Multi-Physics Simulation")
        self.root.geometry("1400x900")

        # Simulation control flags
        self.running = False
        self.simulation_thread = None

        # Time data for simulation
        self.time_data = []
        self.voltage_data = []
        self.current_data = []
        self.temperature_data = []
        self.efficiency_data = []
        self.torque_data = []
        self.power_data = []

        # Machine parameters (default values from the problem)
        self.params = {
            'poles': 4,
            'frequency': 50.0,  # Hz
            'slots_per_pole': 15,
            'conductors_per_slot': 10,
            'winding_factor': 0.95,
            'terminal_voltage': 1825.0,  # V (star-connected)
            'connection_type': 'Star',  # Star or Lap
            'load_resistance': 10.0,  # Ohms
            'load_inductance': 0.05,  # H
            'armature_resistance': 0.5,  # Ohms
            'field_current': 5.0,  # A
            'speed_rpm': 1500.0,  # RPM
            'ambient_temp': 25.0,  # Celsius
            'thermal_resistance': 2.0,  # °C/W
            'thermal_capacitance': 500.0,  # J/°C
            'moment_inertia': 0.5,  # kg.m²
            'friction_coefficient': 0.01,  # N.m.s
            'electricity_cost': 0.12,  # $/kWh
            'core_loss_coeff': 50.0,  # W
            'stray_loss_coeff': 20.0,  # W
        }

        # Physical state variables
        self.state = {
            'voltage': 0.0,
            'current': 0.0,
            'temperature': 25.0,
            'angular_velocity': 0.0,
            'torque': 0.0,
            'flux': 0.0,
        }

        # Loss tracking
        self.losses = {
            'copper_loss': 0.0,
            'iron_loss': 0.0,
            'mechanical_loss': 0.0,
            'stray_loss': 0.0,
            'total_loss': 0.0,
        }

        # Create GUI
        self.create_gui()

        # Bind window resize event
        self.root.bind('<Configure>', self.on_window_resize)

        # Calculate initial values
        self.calculate_theoretical_solution()

    def create_gui(self):
        """Create the main GUI with tabs and controls"""

        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Create tabs
        self.tab_main = ttk.Frame(self.notebook)
        self.tab_electrical = ttk.Frame(self.notebook)
        self.tab_thermal = ttk.Frame(self.notebook)
        self.tab_mechanical = ttk.Frame(self.notebook)
        self.tab_economic = ttk.Frame(self.notebook)
        self.tab_losses = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_main, text='Main Control')
        self.notebook.add(self.tab_electrical, text='Electrical Analysis')
        self.notebook.add(self.tab_thermal, text='Thermal Analysis')
        self.notebook.add(self.tab_mechanical, text='Mechanical Analysis')
        self.notebook.add(self.tab_economic, text='Economic Analysis')
        self.notebook.add(self.tab_losses, text='Loss Breakdown')

        # Setup each tab
        self.setup_main_tab()
        self.setup_electrical_tab()
        self.setup_thermal_tab()
        self.setup_mechanical_tab()
        self.setup_economic_tab()
        self.setup_losses_tab()

        # Control buttons at the bottom
        control_frame = ttk.Frame(self.root)
        control_frame.pack(side='bottom', fill='x', padx=5, pady=5)

        ttk.Button(control_frame, text='Start Simulation',
                  command=self.start_simulation).pack(side='left', padx=5)
        ttk.Button(control_frame, text='Stop Simulation',
                  command=self.stop_simulation).pack(side='left', padx=5)
        ttk.Button(control_frame, text='Reset',
                  command=self.reset_simulation).pack(side='left', padx=5)
        ttk.Button(control_frame, text='Calculate Theory',
                  command=self.calculate_theoretical_solution).pack(side='left', padx=5)

        # Status bar
        self.status_var = tk.StringVar(value='Ready')
        status_bar = ttk.Label(self.root, textvariable=self.status_var,
                              relief='sunken', anchor='w')
        status_bar.pack(side='bottom', fill='x')

    def setup_main_tab(self):
        """Setup main control tab with parameters and theoretical solution"""

        # Left frame for parameters
        left_frame = ttk.LabelFrame(self.tab_main, text='Machine Parameters')
        left_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        # Create parameter inputs with sliders
        self.param_vars = {}
        self.param_labels = {}

        params_config = [
            ('poles', 'Number of Poles', 2, 12, 2),
            ('frequency', 'Frequency (Hz)', 25, 100, 1),
            ('slots_per_pole', 'Slots per Pole', 5, 30, 1),
            ('conductors_per_slot', 'Conductors per Slot', 5, 20, 1),
            ('winding_factor', 'Winding Factor', 0.8, 1.0, 0.01),
            ('terminal_voltage', 'Terminal Voltage (V)', 100, 5000, 10),
            ('load_resistance', 'Load Resistance (Ω)', 1, 100, 1),
            ('field_current', 'Field Current (A)', 1, 20, 0.1),
            ('speed_rpm', 'Speed (RPM)', 500, 3000, 10),
            ('ambient_temp', 'Ambient Temperature (°C)', 0, 50, 1),
        ]

        row = 0
        for param, label, min_val, max_val, resolution in params_config:
            ttk.Label(left_frame, text=label).grid(row=row, column=0,
                                                   sticky='w', padx=5, pady=2)

            var = tk.DoubleVar(value=self.params[param])
            self.param_vars[param] = var

            slider = ttk.Scale(left_frame, from_=min_val, to=max_val,
                             variable=var, orient='horizontal')
            slider.grid(row=row, column=1, sticky='ew', padx=5, pady=2)

            label_var = tk.StringVar(value=f"{self.params[param]:.2f}")
            self.param_labels[param] = label_var
            ttk.Label(left_frame, textvariable=label_var, width=10).grid(
                row=row, column=2, padx=5, pady=2)

            var.trace('w', lambda *args, p=param: self.update_param_label(p))

            row += 1

        left_frame.columnconfigure(1, weight=1)

        # Connection type selector
        ttk.Label(left_frame, text='Connection Type').grid(
            row=row, column=0, sticky='w', padx=5, pady=2)
        self.connection_var = tk.StringVar(value='Star')
        conn_combo = ttk.Combobox(left_frame, textvariable=self.connection_var,
                                 values=['Star', 'Lap'], state='readonly')
        conn_combo.grid(row=row, column=1, sticky='ew', padx=5, pady=2)

        # Right frame for theoretical solution and results
        right_frame = ttk.LabelFrame(self.tab_main, text='Theoretical Solution')
        right_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)

        # Results display
        self.results_text = tk.Text(right_frame, height=20, width=60,
                                   wrap='word', font=('Courier', 10))
        self.results_text.pack(fill='both', expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(right_frame, command=self.results_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.results_text.config(yscrollcommand=scrollbar.set)

    def setup_electrical_tab(self):
        """Setup electrical analysis tab with dynamic graphs"""

        # Create figure for electrical plots
        self.fig_electrical = Figure(figsize=(12, 8), dpi=100)

        self.ax_voltage = self.fig_electrical.add_subplot(3, 2, 1)
        self.ax_current = self.fig_electrical.add_subplot(3, 2, 2)
        self.ax_power = self.fig_electrical.add_subplot(3, 2, 3)
        self.ax_phasor = self.fig_electrical.add_subplot(3, 2, 4, projection='polar')
        self.ax_voltage_current = self.fig_electrical.add_subplot(3, 2, 5)
        self.ax_efficiency = self.fig_electrical.add_subplot(3, 2, 6)

        self.fig_electrical.tight_layout(pad=3.0)

        self.canvas_electrical = FigureCanvasTkAgg(self.fig_electrical, self.tab_electrical)
        self.canvas_electrical.get_tk_widget().pack(fill='both', expand=True)

    def setup_thermal_tab(self):
        """Setup thermal analysis tab"""

        self.fig_thermal = Figure(figsize=(12, 8), dpi=100)

        self.ax_temp_time = self.fig_thermal.add_subplot(2, 2, 1)
        self.ax_temp_dist = self.fig_thermal.add_subplot(2, 2, 2)
        self.ax_heat_flow = self.fig_thermal.add_subplot(2, 2, 3)
        self.ax_derating = self.fig_thermal.add_subplot(2, 2, 4)

        self.fig_thermal.tight_layout(pad=3.0)

        self.canvas_thermal = FigureCanvasTkAgg(self.fig_thermal, self.tab_thermal)
        self.canvas_thermal.get_tk_widget().pack(fill='both', expand=True)

    def setup_mechanical_tab(self):
        """Setup mechanical analysis tab"""

        self.fig_mechanical = Figure(figsize=(12, 8), dpi=100)

        self.ax_torque = self.fig_mechanical.add_subplot(2, 2, 1)
        self.ax_speed = self.fig_mechanical.add_subplot(2, 2, 2)
        self.ax_stress = self.fig_mechanical.add_subplot(2, 2, 3)
        self.ax_bearing = self.fig_mechanical.add_subplot(2, 2, 4)

        self.fig_mechanical.tight_layout(pad=3.0)

        self.canvas_mechanical = FigureCanvasTkAgg(self.fig_mechanical,
                                                   self.tab_mechanical)
        self.canvas_mechanical.get_tk_widget().pack(fill='both', expand=True)

    def setup_economic_tab(self):
        """Setup economic analysis tab"""

        # Create frames
        top_frame = ttk.Frame(self.tab_economic)
        top_frame.pack(fill='both', expand=True)

        bottom_frame = ttk.LabelFrame(self.tab_economic, text='Economic Metrics')
        bottom_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Graphs
        self.fig_economic = Figure(figsize=(12, 4), dpi=100)

        self.ax_cost = self.fig_economic.add_subplot(1, 3, 1)
        self.ax_energy = self.fig_economic.add_subplot(1, 3, 2)
        self.ax_payback = self.fig_economic.add_subplot(1, 3, 3)

        self.fig_economic.tight_layout(pad=3.0)

        canvas_economic = FigureCanvasTkAgg(self.fig_economic, top_frame)
        canvas_economic.get_tk_widget().pack(fill='both', expand=True)

        # Economic metrics display
        self.economic_text = tk.Text(bottom_frame, height=10, width=80,
                                    font=('Courier', 10))
        self.economic_text.pack(fill='both', expand=True, padx=5, pady=5)

    def setup_losses_tab(self):
        """Setup loss breakdown tab"""

        self.fig_losses = Figure(figsize=(12, 8), dpi=100)

        self.ax_loss_pie = self.fig_losses.add_subplot(2, 2, 1)
        self.ax_loss_bar = self.fig_losses.add_subplot(2, 2, 2)
        self.ax_loss_time = self.fig_losses.add_subplot(2, 2, 3)
        self.ax_loss_breakdown = self.fig_losses.add_subplot(2, 2, 4)

        self.fig_losses.tight_layout(pad=3.0)

        self.canvas_losses = FigureCanvasTkAgg(self.fig_losses, self.tab_losses)
        self.canvas_losses.get_tk_widget().pack(fill='both', expand=True)

    def update_param_label(self, param):
        """Update parameter label when slider moves"""
        value = self.param_vars[param].get()
        self.param_labels[param].set(f"{value:.2f}")
        self.params[param] = value

    def calculate_theoretical_solution(self):
        """Calculate and display the theoretical solution to the problem"""

        # Get parameters
        P = self.params['poles']
        f = self.params['frequency']
        slots_per_pole = self.params['slots_per_pole']
        conductors_per_slot = self.params['conductors_per_slot']
        Kw = self.params['winding_factor']
        V_terminal = self.params['terminal_voltage']

        # Calculate basic machine parameters
        total_slots = P * slots_per_pole
        total_conductors = total_slots * conductors_per_slot
        conductors_per_phase = total_conductors / 3  # 3-phase machine

        # For star connection (series)
        V_line = V_terminal
        V_phase = V_line / np.sqrt(3)

        # Calculate flux per pole from the given terminal voltage
        # E_ph = 4.44 * f * Φ * N_ph * Kw
        # Φ = E_ph / (4.44 * f * N_ph * Kw)
        flux_per_pole = V_phase / (4.44 * f * conductors_per_phase * Kw)

        # For lap connection (like DC machine)
        # In lap winding: number of parallel paths = number of poles
        parallel_paths = P
        conductors_in_series = total_conductors / parallel_paths

        # Speed in RPM for given frequency
        N_sync = 120 * f / P  # Synchronous speed

        # For DC-like lap connection with sinusoidal flux distribution
        # Average EMF = (2/π) * Peak EMF
        # Peak EMF = 2 * √2 * 4.44 * f * Φ * (Z/a) * Kw
        # But for DC with rotating armature in sinusoidal field:
        # E_avg = (P * Φ * Z * N) / (60 * a)
        # where Φ is the flux per pole

        # Convert to DC-equivalent EMF
        # The RMS value for sinusoidal is related to average by: RMS = (π/2√2) * Average
        # Average = (2√2/π) * RMS

        omega = 2 * np.pi * N_sync / 60  # Angular velocity in rad/s

        # For lap connection, EMF between brushes
        # Using the relation: E_lap = (Φ * Z * N * P) / (60 * a)
        # where a = P for lap winding
        E_lap_avg = (flux_per_pole * total_conductors * N_sync * P) / (60 * P)

        # For sinusoidal flux, the instantaneous EMF will be sinusoidal
        # RMS value of sinusoidal EMF for lap connection
        # E_lap_rms = 4.44 * f * Φ * (Z/a) * Kw
        E_lap_rms = 4.44 * f * flux_per_pole * conductors_in_series * Kw

        # Display results
        results = f"""
{'='*60}
THEORETICAL SOLUTION - ALTERNATOR EMF CALCULATION
{'='*60}

GIVEN PARAMETERS:
{'-'*60}
Number of Poles (P)              : {P}
Frequency (f)                    : {f} Hz
Slots per Pole                   : {slots_per_pole}
Conductors per Slot              : {conductors_per_slot}
Winding Factor (Kw)              : {Kw}
Terminal Voltage (Star-connected): {V_terminal} V

CALCULATED MACHINE PARAMETERS:
{'-'*60}
Total Slots                      : {total_slots}
Total Conductors (Z)             : {total_conductors}
Conductors per Phase             : {conductors_per_phase:.0f}
Synchronous Speed                : {N_sync:.2f} RPM

STAR CONNECTION (SERIES - ORIGINAL):
{'-'*60}
Line Voltage                     : {V_line:.2f} V
Phase Voltage                    : {V_phase:.2f} V
Flux per Pole (Φ)                : {flux_per_pole:.6f} Wb
                                  : {flux_per_pole*1000:.4f} mWb

LAP CONNECTION (LIKE DC MACHINE):
{'-'*60}
Parallel Paths (a = P)           : {parallel_paths}
Conductors in Series per Path    : {conductors_in_series:.0f}
EMF between Brushes (Average)    : {E_lap_avg:.2f} V
EMF between Brushes (RMS)        : {E_lap_rms:.2f} V

COMPARISON:
{'-'*60}
Star Connection Voltage          : {V_terminal:.2f} V (Line-to-Line)
Lap Connection Voltage (RMS)     : {E_lap_rms:.2f} V (Brush-to-Brush)
Ratio (Lap/Star)                 : {E_lap_rms/V_terminal:.4f}

NOTES:
{'-'*60}
1. For star connection, all conductors per phase are in series.
2. For lap connection, parallel paths = number of poles = {P}.
3. The lap connection voltage is the RMS value assuming
   sinusoidal flux distribution as specified.
4. The same flux per pole (Φ = {flux_per_pole*1000:.4f} mWb) and
   speed (N = {N_sync:.2f} RPM) are used in both cases.

{'='*60}
"""

        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(1.0, results)

        # Update state
        self.state['flux'] = flux_per_pole
        self.state['voltage'] = E_lap_rms if self.connection_var.get() == 'Lap' else V_phase

        messagebox.showinfo("Calculation Complete",
                          f"Theoretical solution calculated!\n\n"
                          f"Star Connection: {V_terminal:.2f} V\n"
                          f"Lap Connection (RMS): {E_lap_rms:.2f} V")

    def electrical_ode_system(self, t, y):
        """
        Differential equations for electrical system
        y = [i_d, i_q, omega, theta]
        i_d, i_q: dq-axis currents
        omega: angular velocity
        theta: rotor angle
        """
        i_d, i_q, omega, theta = y

        # Parameters
        R_a = self.params['armature_resistance']
        L_d = self.params['load_inductance']
        L_q = self.params['load_inductance']
        P = self.params['poles']
        flux = self.state['flux']

        # Load parameters
        R_load = self.params['load_resistance']
        L_load = self.params['load_inductance']

        # Voltage equations in dq frame
        # v_d = R*i_d + L_d*di_d/dt - omega*L_q*i_q
        # v_q = R*i_q + L_q*di_q/dt + omega*L_d*i_d + omega*flux

        v_d = 0  # Assuming d-axis voltage is zero
        v_q = self.state['voltage'] * np.sqrt(2)  # Peak voltage

        # Current derivatives
        di_d = (v_d - (R_a + R_load)*i_d + omega*L_q*i_q) / (L_d + L_load)
        di_q = (v_q - (R_a + R_load)*i_q - omega*L_d*i_d - omega*flux) / (L_q + L_load)

        # Mechanical equation
        # J*domega/dt = T_e - T_load - B*omega
        J = self.params['moment_inertia']
        B = self.params['friction_coefficient']

        # Electromagnetic torque
        T_e = (3/2) * (P/2) * (flux * i_q + (L_d - L_q) * i_d * i_q)
        T_load = 0.1 * omega + 5  # Simple load model

        domega = (T_e - T_load - B*omega) / J

        # Angle derivative
        dtheta = omega

        return [di_d, di_q, domega, dtheta]

    def thermal_ode_system(self, T, t):
        """
        Thermal differential equation
        C_th * dT/dt = P_loss - (T - T_amb) / R_th
        """
        C_th = self.params['thermal_capacitance']
        R_th = self.params['thermal_resistance']
        T_amb = self.params['ambient_temp']

        # Calculate total losses
        P_loss = self.losses['total_loss']

        # Temperature derivative
        dT_dt = (P_loss - (T - T_amb) / R_th) / C_th

        return dT_dt

    def calculate_losses(self, current_rms, voltage_rms, omega):
        """Calculate all losses in the machine"""

        # Copper losses (I²R)
        R_a = self.params['armature_resistance']
        copper_loss = 3 * current_rms**2 * R_a  # 3-phase

        # Iron losses (hysteresis + eddy current)
        # P_iron = K_h * f * B_max² + K_e * f² * B_max²
        f = self.params['frequency']
        core_loss = self.params['core_loss_coeff'] * (f / 50)**1.5

        # Mechanical losses (friction and windage)
        # P_mech = K_f * omega + K_w * omega²
        B = self.params['friction_coefficient']
        mech_loss = B * omega**2 + 10 * omega

        # Stray load losses
        stray_loss = self.params['stray_loss_coeff'] * (current_rms / 10)**2

        # Update losses dictionary
        self.losses['copper_loss'] = copper_loss
        self.losses['iron_loss'] = core_loss
        self.losses['mechanical_loss'] = mech_loss
        self.losses['stray_loss'] = stray_loss
        self.losses['total_loss'] = copper_loss + core_loss + mech_loss + stray_loss

    def run_simulation_step(self, dt):
        """Run one step of the multi-physics simulation"""

        # Get current time
        if len(self.time_data) == 0:
            t = 0
        else:
            t = self.time_data[-1] + dt

        # Solve electrical system using RK45
        omega_sync = 2 * np.pi * self.params['frequency']
        y0 = [0, 5, omega_sync, 0]  # Initial conditions

        try:
            # Electrical solution (short time step for accuracy)
            sol = solve_ivp(self.electrical_ode_system, [0, dt], y0,
                          method='RK45', dense_output=True)

            if sol.success:
                i_d, i_q, omega, theta = sol.y[:, -1]

                # Calculate RMS values
                i_rms = np.sqrt(i_d**2 + i_q**2) / np.sqrt(2)
                v_rms = self.state['voltage']

                # Calculate power
                power = 3 * v_rms * i_rms * 0.8  # Assuming 0.8 power factor

                # Update state
                self.state['current'] = i_rms
                self.state['angular_velocity'] = omega
                self.state['torque'] = (3/2) * (self.params['poles']/2) * \
                                       (self.state['flux'] * i_q)

                # Calculate losses
                self.calculate_losses(i_rms, v_rms, omega)

                # Solve thermal system
                T_current = self.state['temperature']
                T_new = odeint(self.thermal_ode_system, T_current, [0, dt])[-1]
                self.state['temperature'] = T_new

                # Apply thermal derating
                if T_new > 100:
                    derating_factor = max(0.5, 1 - (T_new - 100) / 100)
                    self.state['voltage'] *= derating_factor

                # Calculate efficiency
                P_out = power
                P_in = power + self.losses['total_loss']
                efficiency = (P_out / P_in * 100) if P_in > 0 else 0

                # Store data
                self.time_data.append(t)
                self.voltage_data.append(v_rms)
                self.current_data.append(i_rms)
                self.temperature_data.append(T_new)
                self.efficiency_data.append(efficiency)
                self.torque_data.append(self.state['torque'])
                self.power_data.append(power)

                # Limit data length
                max_points = 1000
                if len(self.time_data) > max_points:
                    self.time_data = self.time_data[-max_points:]
                    self.voltage_data = self.voltage_data[-max_points:]
                    self.current_data = self.current_data[-max_points:]
                    self.temperature_data = self.temperature_data[-max_points:]
                    self.efficiency_data = self.efficiency_data[-max_points:]
                    self.torque_data = self.torque_data[-max_points:]
                    self.power_data = self.power_data[-max_points:]

        except Exception as e:
            print(f"Simulation error: {e}")

    def update_plots(self):
        """Update all plots with current data"""

        if len(self.time_data) < 2:
            return

        # Update electrical plots
        self.update_electrical_plots()
        self.update_thermal_plots()
        self.update_mechanical_plots()
        self.update_economic_plots()
        self.update_losses_plots()

    def update_electrical_plots(self):
        """Update electrical analysis plots"""

        t = np.array(self.time_data)
        v = np.array(self.voltage_data)
        i = np.array(self.current_data)
        p = np.array(self.power_data)
        eff = np.array(self.efficiency_data)

        # Voltage vs Time
        self.ax_voltage.clear()
        self.ax_voltage.plot(t, v, 'b-', linewidth=2)
        self.ax_voltage.set_xlabel('Time (s)')
        self.ax_voltage.set_ylabel('Voltage (V)')
        self.ax_voltage.set_title('RMS Voltage vs Time')
        self.ax_voltage.grid(True, alpha=0.3)

        # Current vs Time
        self.ax_current.clear()
        self.ax_current.plot(t, i, 'r-', linewidth=2)
        self.ax_current.set_xlabel('Time (s)')
        self.ax_current.set_ylabel('Current (A)')
        self.ax_current.set_title('RMS Current vs Time')
        self.ax_current.grid(True, alpha=0.3)

        # Power vs Time
        self.ax_power.clear()
        self.ax_power.plot(t, p, 'g-', linewidth=2)
        self.ax_power.set_xlabel('Time (s)')
        self.ax_power.set_ylabel('Power (W)')
        self.ax_power.set_title('Output Power vs Time')
        self.ax_power.grid(True, alpha=0.3)

        # Phasor diagram
        self.ax_phasor.clear()
        if len(v) > 0 and len(i) > 0:
            # Voltage phasor (reference)
            v_mag = v[-1]
            v_angle = 0
            # Current phasor (lagging by power factor angle)
            i_mag = i[-1] * 10  # Scale for visibility
            pf_angle = np.arccos(0.8)  # Assuming 0.8 pf

            self.ax_phasor.arrow(0, v_angle, 0.8, 0, head_width=0.1,
                               head_length=0.1, fc='blue', ec='blue',
                               linewidth=2, label='Voltage')
            self.ax_phasor.arrow(0, -pf_angle, 0.6, 0, head_width=0.1,
                               head_length=0.1, fc='red', ec='red',
                               linewidth=2, label='Current')
            self.ax_phasor.set_ylim(-np.pi, np.pi)
            self.ax_phasor.set_title('Phasor Diagram')
            self.ax_phasor.legend(loc='upper right')

        # Voltage-Current characteristic
        self.ax_voltage_current.clear()
        self.ax_voltage_current.plot(i, v, 'mo-', linewidth=2, markersize=3)
        self.ax_voltage_current.set_xlabel('Current (A)')
        self.ax_voltage_current.set_ylabel('Voltage (V)')
        self.ax_voltage_current.set_title('V-I Characteristic')
        self.ax_voltage_current.grid(True, alpha=0.3)

        # Efficiency vs Time
        self.ax_efficiency.clear()
        self.ax_efficiency.plot(t, eff, 'c-', linewidth=2)
        self.ax_efficiency.set_xlabel('Time (s)')
        self.ax_efficiency.set_ylabel('Efficiency (%)')
        self.ax_efficiency.set_title('Efficiency vs Time')
        self.ax_efficiency.grid(True, alpha=0.3)
        self.ax_efficiency.set_ylim([0, 100])

        self.fig_electrical.tight_layout()
        self.canvas_electrical.draw()

    def update_thermal_plots(self):
        """Update thermal analysis plots"""

        t = np.array(self.time_data)
        T = np.array(self.temperature_data)

        # Temperature vs Time
        self.ax_temp_time.clear()
        self.ax_temp_time.plot(t, T, 'r-', linewidth=2, label='Winding Temp')
        self.ax_temp_time.axhline(y=self.params['ambient_temp'],
                                 color='b', linestyle='--', label='Ambient')
        self.ax_temp_time.axhline(y=100, color='orange',
                                 linestyle='--', label='Rated Temp')
        self.ax_temp_time.axhline(y=130, color='red',
                                 linestyle='--', label='Max Temp')
        self.ax_temp_time.set_xlabel('Time (s)')
        self.ax_temp_time.set_ylabel('Temperature (°C)')
        self.ax_temp_time.set_title('Temperature Rise')
        self.ax_temp_time.legend()
        self.ax_temp_time.grid(True, alpha=0.3)

        # Temperature distribution (simplified radial model)
        self.ax_temp_dist.clear()
        r = np.linspace(0, 1, 50)
        T_center = T[-1] if len(T) > 0 else 25
        T_surface = self.params['ambient_temp']
        T_dist = T_surface + (T_center - T_surface) * (1 - r**2)
        self.ax_temp_dist.plot(r, T_dist, 'r-', linewidth=2)
        self.ax_temp_dist.set_xlabel('Normalized Radius')
        self.ax_temp_dist.set_ylabel('Temperature (°C)')
        self.ax_temp_dist.set_title('Radial Temperature Distribution')
        self.ax_temp_dist.grid(True, alpha=0.3)

        # Heat flow
        self.ax_heat_flow.clear()
        if len(t) > 0:
            heat_gen = [self.losses['total_loss']] * len(t)
            heat_diss = [(T[i] - self.params['ambient_temp']) /
                        self.params['thermal_resistance']
                        for i in range(len(T))]
            self.ax_heat_flow.plot(t, heat_gen, 'r-',
                                  linewidth=2, label='Heat Generated')
            self.ax_heat_flow.plot(t, heat_diss, 'b-',
                                  linewidth=2, label='Heat Dissipated')
            self.ax_heat_flow.set_xlabel('Time (s)')
            self.ax_heat_flow.set_ylabel('Heat Flow (W)')
            self.ax_heat_flow.set_title('Heat Balance')
            self.ax_heat_flow.legend()
            self.ax_heat_flow.grid(True, alpha=0.3)

        # Derating curve
        self.ax_derating.clear()
        T_range = np.linspace(0, 150, 100)
        T_rated = 100
        derating = np.ones_like(T_range)
        derating[T_range > T_rated] = 1 - (T_range[T_range > T_rated] - T_rated) / 100
        derating[derating < 0.5] = 0.5
        self.ax_derating.plot(T_range, derating * 100, 'b-', linewidth=2)
        if len(T) > 0:
            current_temp = T[-1]
            current_derating = 1
            if current_temp > T_rated:
                current_derating = max(0.5, 1 - (current_temp - T_rated) / 100)
            self.ax_derating.plot(current_temp, current_derating * 100,
                                'ro', markersize=10, label='Operating Point')
        self.ax_derating.set_xlabel('Temperature (°C)')
        self.ax_derating.set_ylabel('Capacity (%)')
        self.ax_derating.set_title('Thermal Derating Curve')
        self.ax_derating.legend()
        self.ax_derating.grid(True, alpha=0.3)

        self.fig_thermal.tight_layout()
        self.canvas_thermal.draw()

    def update_mechanical_plots(self):
        """Update mechanical analysis plots"""

        t = np.array(self.time_data)
        torque = np.array(self.torque_data)

        # Torque vs Time
        self.ax_torque.clear()
        self.ax_torque.plot(t, torque, 'g-', linewidth=2)
        self.ax_torque.set_xlabel('Time (s)')
        self.ax_torque.set_ylabel('Torque (N.m)')
        self.ax_torque.set_title('Electromagnetic Torque')
        self.ax_torque.grid(True, alpha=0.3)

        # Speed vs Time
        self.ax_speed.clear()
        omega = [self.state['angular_velocity']] * len(t) if len(t) > 0 else []
        speed_rpm = np.array(omega) * 60 / (2 * np.pi)
        self.ax_speed.plot(t, speed_rpm, 'b-', linewidth=2)
        self.ax_speed.set_xlabel('Time (s)')
        self.ax_speed.set_ylabel('Speed (RPM)')
        self.ax_speed.set_title('Rotor Speed')
        self.ax_speed.grid(True, alpha=0.3)

        # Shaft stress (simplified)
        self.ax_stress.clear()
        if len(torque) > 0:
            # Assume shaft diameter of 50mm
            d = 0.05  # meters
            J_shaft = np.pi * d**4 / 32
            tau = torque * (d/2) / J_shaft  # Shear stress
            self.ax_stress.plot(t, tau / 1e6, 'r-', linewidth=2)  # Convert to MPa
            self.ax_stress.set_xlabel('Time (s)')
            self.ax_stress.set_ylabel('Shear Stress (MPa)')
            self.ax_stress.set_title('Shaft Stress')
            self.ax_stress.grid(True, alpha=0.3)

        # Bearing loads (simplified radial load)
        self.ax_bearing.clear()
        if len(torque) > 0:
            # Simplified bearing load calculation
            bearing_load = np.abs(torque) / 0.1  # Assume 100mm bearing spacing
            self.ax_bearing.plot(t, bearing_load, 'm-', linewidth=2)
            self.ax_bearing.set_xlabel('Time (s)')
            self.ax_bearing.set_ylabel('Bearing Load (N)')
            self.ax_bearing.set_title('Bearing Radial Load')
            self.ax_bearing.grid(True, alpha=0.3)

        self.fig_mechanical.tight_layout()
        self.canvas_mechanical.draw()

    def update_economic_plots(self):
        """Update economic analysis plots"""

        t = np.array(self.time_data)
        p = np.array(self.power_data)

        # Operating cost vs Time
        self.ax_cost.clear()
        if len(t) > 0:
            energy_kwh = np.cumsum(p) * np.diff(t, prepend=0) / 3600000  # kWh
            cost = energy_kwh * self.params['electricity_cost']
            self.ax_cost.plot(t, cost, 'g-', linewidth=2)
            self.ax_cost.set_xlabel('Time (s)')
            self.ax_cost.set_ylabel('Cost ($)')
            self.ax_cost.set_title('Cumulative Operating Cost')
            self.ax_cost.grid(True, alpha=0.3)

        # Energy consumption
        self.ax_energy.clear()
        if len(t) > 0:
            self.ax_energy.plot(t, p / 1000, 'b-', linewidth=2)  # kW
            self.ax_energy.set_xlabel('Time (s)')
            self.ax_energy.set_ylabel('Power (kW)')
            self.ax_energy.set_title('Power Consumption')
            self.ax_energy.grid(True, alpha=0.3)

        # Efficiency vs Load
        self.ax_payback.clear()
        if len(self.efficiency_data) > 0 and len(self.current_data) > 0:
            i = np.array(self.current_data)
            eff = np.array(self.efficiency_data)
            self.ax_payback.plot(i, eff, 'r-', linewidth=2)
            self.ax_payback.set_xlabel('Load Current (A)')
            self.ax_payback.set_ylabel('Efficiency (%)')
            self.ax_payback.set_title('Efficiency vs Load')
            self.ax_payback.grid(True, alpha=0.3)

        self.fig_economic.tight_layout()

        # Update economic metrics text
        self.update_economic_metrics()

    def update_economic_metrics(self):
        """Update economic metrics display"""

        if len(self.time_data) == 0:
            return

        t = np.array(self.time_data)
        p = np.array(self.power_data)

        total_time_hours = t[-1] / 3600
        avg_power_kw = np.mean(p) / 1000
        energy_kwh = avg_power_kw * total_time_hours
        energy_cost = energy_kwh * self.params['electricity_cost']

        avg_efficiency = np.mean(self.efficiency_data) if self.efficiency_data else 0
        total_losses_kw = self.losses['total_loss'] / 1000

        metrics = f"""
{'='*70}
ECONOMIC ANALYSIS METRICS
{'='*70}

ENERGY CONSUMPTION:
{'-'*70}
Simulation Time                : {total_time_hours:.4f} hours
Average Power                  : {avg_power_kw:.3f} kW
Total Energy Consumed          : {energy_kwh:.6f} kWh
Electricity Cost Rate          : ${self.params['electricity_cost']:.3f}/kWh
Total Energy Cost              : ${energy_cost:.6f}

EFFICIENCY & LOSSES:
{'-'*70}
Average Efficiency             : {avg_efficiency:.2f}%
Total Power Losses             : {total_losses_kw:.3f} kW
  - Copper Losses              : {self.losses['copper_loss']/1000:.3f} kW
  - Iron Losses                : {self.losses['iron_loss']/1000:.3f} kW
  - Mechanical Losses          : {self.losses['mechanical_loss']/1000:.3f} kW
  - Stray Losses               : {self.losses['stray_loss']/1000:.3f} kW

COST PROJECTIONS (24 Hour Operation):
{'-'*70}
Daily Energy                   : {avg_power_kw * 24:.3f} kWh
Daily Cost                     : ${avg_power_kw * 24 * self.params['electricity_cost']:.2f}
Monthly Cost (30 days)         : ${avg_power_kw * 24 * 30 * self.params['electricity_cost']:.2f}
Yearly Cost (365 days)         : ${avg_power_kw * 24 * 365 * self.params['electricity_cost']:.2f}

PERFORMANCE METRICS:
{'-'*70}
Current Operating Temperature  : {self.state['temperature']:.2f}°C
Current Output Power           : {p[-1]/1000:.3f} kW
Current Efficiency             : {self.efficiency_data[-1] if self.efficiency_data else 0:.2f}%
Current Torque                 : {self.state['torque']:.3f} N.m

{'='*70}
"""

        self.economic_text.delete(1.0, tk.END)
        self.economic_text.insert(1.0, metrics)

    def update_losses_plots(self):
        """Update loss breakdown plots"""

        # Pie chart of losses
        self.ax_loss_pie.clear()
        losses = [
            self.losses['copper_loss'],
            self.losses['iron_loss'],
            self.losses['mechanical_loss'],
            self.losses['stray_loss']
        ]
        labels = ['Copper', 'Iron', 'Mechanical', 'Stray']
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']

        if sum(losses) > 0:
            self.ax_loss_pie.pie(losses, labels=labels, colors=colors,
                                autopct='%1.1f%%', startangle=90)
            self.ax_loss_pie.set_title('Loss Distribution')

        # Bar chart of losses
        self.ax_loss_bar.clear()
        self.ax_loss_bar.bar(labels, losses, color=colors)
        self.ax_loss_bar.set_ylabel('Loss (W)')
        self.ax_loss_bar.set_title('Loss Breakdown')
        self.ax_loss_bar.grid(True, alpha=0.3, axis='y')

        # Losses vs Time
        self.ax_loss_time.clear()
        if len(self.time_data) > 0:
            t = np.array(self.time_data)
            total_loss = [self.losses['total_loss']] * len(t)
            self.ax_loss_time.plot(t, total_loss, 'r-', linewidth=2)
            self.ax_loss_time.set_xlabel('Time (s)')
            self.ax_loss_time.set_ylabel('Total Loss (W)')
            self.ax_loss_time.set_title('Total Losses vs Time')
            self.ax_loss_time.grid(True, alpha=0.3)

        # Stacked area chart
        self.ax_loss_breakdown.clear()
        if len(self.time_data) > 0:
            t = np.array(self.time_data)
            copper = [self.losses['copper_loss']] * len(t)
            iron = [self.losses['iron_loss']] * len(t)
            mech = [self.losses['mechanical_loss']] * len(t)
            stray = [self.losses['stray_loss']] * len(t)

            self.ax_loss_breakdown.fill_between(t, 0, copper,
                                               label='Copper', color=colors[0], alpha=0.7)
            self.ax_loss_breakdown.fill_between(t, copper,
                                               np.array(copper) + np.array(iron),
                                               label='Iron', color=colors[1], alpha=0.7)
            self.ax_loss_breakdown.fill_between(t,
                                               np.array(copper) + np.array(iron),
                                               np.array(copper) + np.array(iron) + np.array(mech),
                                               label='Mechanical', color=colors[2], alpha=0.7)
            self.ax_loss_breakdown.fill_between(t,
                                               np.array(copper) + np.array(iron) + np.array(mech),
                                               np.array(copper) + np.array(iron) + np.array(mech) + np.array(stray),
                                               label='Stray', color=colors[3], alpha=0.7)

            self.ax_loss_breakdown.set_xlabel('Time (s)')
            self.ax_loss_breakdown.set_ylabel('Loss (W)')
            self.ax_loss_breakdown.set_title('Loss Breakdown Over Time')
            self.ax_loss_breakdown.legend(loc='upper right')
            self.ax_loss_breakdown.grid(True, alpha=0.3)

        self.fig_losses.tight_layout()
        self.canvas_losses.draw()

    def simulation_loop(self):
        """Main simulation loop running in separate thread"""

        dt = 0.1  # Time step in seconds

        while self.running:
            # Run simulation step
            self.run_simulation_step(dt)

            # Update status
            self.status_var.set(f'Running... Time: {self.time_data[-1]:.2f}s, '
                              f'Temp: {self.state["temperature"]:.1f}°C, '
                              f'Current: {self.state["current"]:.2f}A')

            # Small delay for visualization
            time.sleep(0.05)

        self.status_var.set('Stopped')

    def start_simulation(self):
        """Start the simulation"""

        if not self.running:
            self.running = True
            self.simulation_thread = threading.Thread(target=self.simulation_loop)
            self.simulation_thread.daemon = True
            self.simulation_thread.start()

            # Start plot update timer
            self.update_plots_timer()

            messagebox.showinfo("Simulation Started",
                              "Multi-physics simulation is running!")

    def stop_simulation(self):
        """Stop the simulation"""

        self.running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=1.0)

        messagebox.showinfo("Simulation Stopped", "Simulation has been stopped.")

    def reset_simulation(self):
        """Reset the simulation"""

        self.stop_simulation()

        # Clear data
        self.time_data = []
        self.voltage_data = []
        self.current_data = []
        self.temperature_data = []
        self.efficiency_data = []
        self.torque_data = []
        self.power_data = []

        # Reset state
        self.state['temperature'] = self.params['ambient_temp']
        self.state['current'] = 0.0
        self.state['torque'] = 0.0

        # Clear plots
        self.update_plots()

        self.status_var.set('Reset complete')
        messagebox.showinfo("Reset", "Simulation has been reset.")

    def update_plots_timer(self):
        """Timer function to update plots periodically"""

        if self.running:
            self.update_plots()
            self.root.after(200, self.update_plots_timer)  # Update every 200ms

    def on_window_resize(self, event):
        """Handle window resize event for auto-scaling"""

        # Only process resize events for the main window
        if event.widget == self.root:
            # Redraw canvases to fit new size
            try:
                self.canvas_electrical.draw()
                self.canvas_thermal.draw()
                self.canvas_mechanical.draw()
                self.canvas_losses.draw()
            except:
                pass  # Ignore errors during initialization


def main():
    """Main function to run the application"""

    root = tk.Tk()
    app = AlternatorSimulation(root)
    root.mainloop()


if __name__ == "__main__":
    main()
