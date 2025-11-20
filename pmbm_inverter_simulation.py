"""
PMBM Inverter Simulation with Interactive Visualization
Three-phase, 8-pole PMBM fed from six-pulse inverter
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle, FancyArrowPatch
from matplotlib.gridspec import GridSpec
import matplotlib.patches as mpatches

class PMBMInverterSimulation:
    def __init__(self):
        # Default parameters
        self.Vdc = 600  # DC bus voltage (V)
        self.R1L = 0.9  # Line-to-line resistance (Ohm)
        self.L1L = 5.0  # Line-to-line inductance (mH)
        self.kE = 0.072  # EMF constant (V/rpm)
        self.kT = 0.83  # Torque constant (Nm/A)
        self.speed = 6000  # Motor speed (rpm)
        self.poles = 8  # Number of poles

    def calculate(self, Vdc, R1L, L1L, kE, kT, speed):
        """Calculate motor parameters"""
        # For six-pulse inverter with two phases on
        # Line-to-line voltage equals DC bus voltage
        VLL = Vdc

        # Back EMF (line-to-line)
        EMF_LL = kE * speed

        # Current through conducting phases
        I = (VLL - EMF_LL) / R1L

        # Electromagnetic torque
        Te = kT * I

        # Copper losses (two phases conducting)
        Pcu = I**2 * R1L

        # Electromagnetic power
        Pem = EMF_LL * I

        # Mechanical angular velocity (rad/s)
        omega = 2 * np.pi * speed / 60

        # Shaft power (assuming no mechanical losses)
        Pshaft = Pem

        # Shaft torque (assuming no mechanical losses)
        Tshaft = Te

        # Input power
        Pin = VLL * I

        # Efficiency
        efficiency = (Pem / Pin * 100) if Pin > 0 else 0

        return {
            'VLL': VLL,
            'EMF_LL': EMF_LL,
            'I': I,
            'Te': Te,
            'Tshaft': Tshaft,
            'Pcu': Pcu,
            'Pem': Pem,
            'Pshaft': Pshaft,
            'Pin': Pin,
            'omega': omega,
            'efficiency': efficiency
        }

    def generate_waveforms(self, Vdc, I, EMF_LL, speed):
        """Generate voltage and current waveforms for visualization"""
        # Electrical frequency
        fe = speed * self.poles / 120  # Hz
        T = 1 / fe  # Period

        # Time array (2 periods)
        t = np.linspace(0, 2*T, 1000)

        # Phase voltages (six-step waveform)
        # Simplified representation
        angle = 2 * np.pi * fe * t

        # Six-step voltage waveform (line-to-line)
        vll = np.zeros_like(t)
        for i in range(len(t)):
            phase = angle[i] % (2*np.pi)
            if 0 <= phase < np.pi/3 or 2*np.pi/3 <= phase < np.pi:
                vll[i] = Vdc
            elif np.pi/3 <= phase < 2*np.pi/3 or np.pi <= phase < 4*np.pi/3:
                vll[i] = 0
            else:
                vll[i] = -Vdc

        # Current waveform (simplified - constant during conduction)
        current = np.ones_like(t) * I

        # Back EMF (sinusoidal approximation)
        emf = EMF_LL * np.sin(angle)

        return t, vll, current, emf, T

    def create_visualization(self):
        """Create interactive visualization with sliders"""
        # Create figure with custom layout
        fig = plt.figure(figsize=(16, 10))
        fig.suptitle('PMBM Six-Pulse Inverter Simulation', fontsize=16, fontweight='bold')

        # Create grid layout
        gs = GridSpec(4, 3, figure=fig, hspace=0.35, wspace=0.3,
                     left=0.08, right=0.95, top=0.92, bottom=0.25)

        # Create subplots
        ax_circuit = fig.add_subplot(gs[0, :])
        ax_voltage = fig.add_subplot(gs[1, 0:2])
        ax_current = fig.add_subplot(gs[2, 0:2])
        ax_power = fig.add_subplot(gs[1, 2])
        ax_torque = fig.add_subplot(gs[2, 2])
        ax_speed = fig.add_subplot(gs[3, 0])
        ax_efficiency = fig.add_subplot(gs[3, 1])
        ax_losses = fig.add_subplot(gs[3, 2])

        # Initial calculation
        results = self.calculate(self.Vdc, self.R1L, self.L1L,
                                self.kE, self.kT, self.speed)

        # Create slider axes
        slider_height = 0.015
        slider_spacing = 0.025
        slider_left = 0.15
        slider_width = 0.7
        slider_bottom = 0.02

        ax_vdc = plt.axes([slider_left, slider_bottom + 5*slider_spacing,
                          slider_width, slider_height])
        ax_r1l = plt.axes([slider_left, slider_bottom + 4*slider_spacing,
                          slider_width, slider_height])
        ax_l1l = plt.axes([slider_left, slider_bottom + 3*slider_spacing,
                          slider_width, slider_height])
        ax_ke = plt.axes([slider_left, slider_bottom + 2*slider_spacing,
                         slider_width, slider_height])
        ax_kt = plt.axes([slider_left, slider_bottom + 1*slider_spacing,
                         slider_width, slider_height])
        ax_speed_slider = plt.axes([slider_left, slider_bottom,
                                   slider_width, slider_height])

        # Create sliders
        slider_vdc = Slider(ax_vdc, 'Vdc (V)', 100, 1000, valinit=self.Vdc,
                           valstep=10, color='blue')
        slider_r1l = Slider(ax_r1l, 'R1L (Ω)', 0.1, 5.0, valinit=self.R1L,
                           valstep=0.1, color='red')
        slider_l1l = Slider(ax_l1l, 'L1L (mH)', 1.0, 20.0, valinit=self.L1L,
                           valstep=0.5, color='green')
        slider_ke = Slider(ax_ke, 'kE (V/rpm)', 0.01, 0.2, valinit=self.kE,
                          valstep=0.001, color='orange')
        slider_kt = Slider(ax_kt, 'kT (Nm/A)', 0.1, 2.0, valinit=self.kT,
                          valstep=0.01, color='purple')
        slider_speed = Slider(ax_speed_slider, 'Speed (rpm)', 1000, 10000,
                             valinit=self.speed, valstep=100, color='cyan')

        def update(val):
            """Update all plots when slider changes"""
            # Get current slider values
            Vdc = slider_vdc.val
            R1L = slider_r1l.val
            L1L = slider_l1l.val
            kE = slider_ke.val
            kT = slider_kt.val
            speed = slider_speed.val

            # Recalculate
            results = self.calculate(Vdc, R1L, L1L, kE, kT, speed)

            # Clear all axes
            ax_circuit.clear()
            ax_voltage.clear()
            ax_current.clear()
            ax_power.clear()
            ax_torque.clear()
            ax_speed.clear()
            ax_efficiency.clear()
            ax_losses.clear()

            # Redraw all plots
            self.plot_circuit_diagram(ax_circuit, Vdc, results)
            self.plot_voltage_waveform(ax_voltage, Vdc, results, speed)
            self.plot_current_waveform(ax_current, results, speed)
            self.plot_power_flow(ax_power, results)
            self.plot_torque_info(ax_torque, results)
            self.plot_speed_curve(ax_speed, Vdc, R1L, kE, kT, speed)
            self.plot_efficiency(ax_efficiency, Vdc, R1L, kE, kT, speed)
            self.plot_losses(ax_losses, results)

            fig.canvas.draw_idle()

        # Connect sliders to update function
        slider_vdc.on_changed(update)
        slider_r1l.on_changed(update)
        slider_l1l.on_changed(update)
        slider_ke.on_changed(update)
        slider_kt.on_changed(update)
        slider_speed.on_changed(update)

        # Initial plot
        self.plot_circuit_diagram(ax_circuit, self.Vdc, results)
        self.plot_voltage_waveform(ax_voltage, self.Vdc, results, self.speed)
        self.plot_current_waveform(ax_current, results, self.speed)
        self.plot_power_flow(ax_power, results)
        self.plot_torque_info(ax_torque, results)
        self.plot_speed_curve(ax_speed, self.Vdc, self.R1L,
                             self.kE, self.kT, self.speed)
        self.plot_efficiency(ax_efficiency, self.Vdc, self.R1L,
                            self.kE, self.kT, self.speed)
        self.plot_losses(ax_losses, results)

        plt.show()

    def plot_circuit_diagram(self, ax, Vdc, results):
        """Draw simplified circuit diagram with inverter"""
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6)
        ax.axis('off')
        ax.set_title('Six-Pulse Inverter Circuit', fontweight='bold', pad=10)

        # DC Source
        dc_source = FancyBboxPatch((0.5, 2.5), 1, 1, boxstyle="round,pad=0.1",
                                   edgecolor='black', facecolor='lightblue', linewidth=2)
        ax.add_patch(dc_source)
        ax.text(1, 3, f'Vdc\n{Vdc:.0f}V', ha='center', va='center',
               fontweight='bold', fontsize=9)

        # Inverter block
        inverter = FancyBboxPatch((2.5, 1.5), 2, 3, boxstyle="round,pad=0.1",
                                 edgecolor='black', facecolor='lightcoral', linewidth=2)
        ax.add_patch(inverter)
        ax.text(3.5, 3, 'Six-Pulse\nInverter', ha='center', va='center',
               fontweight='bold', fontsize=10)

        # Draw switches (simplified)
        for i in range(3):
            y_pos = 2 + i * 0.8
            ax.plot([3.2, 3.5], [y_pos, y_pos], 'k-', linewidth=2)
            ax.plot([3.5, 3.8], [y_pos+0.2, y_pos], 'k-', linewidth=2)

        # Motor
        motor = Circle((7, 3), 1.2, edgecolor='black', facecolor='lightgreen', linewidth=2)
        ax.add_patch(motor)
        ax.text(7, 3, 'PMBM\n8-pole', ha='center', va='center',
               fontweight='bold', fontsize=10)

        # Connection lines
        ax.arrow(1.5, 3, 0.8, 0, head_width=0.15, head_length=0.15,
                fc='red', ec='red', linewidth=2)
        ax.arrow(4.5, 3.5, 1, 0, head_width=0.15, head_length=0.15,
                fc='blue', ec='blue', linewidth=2)
        ax.arrow(4.5, 3, 1, 0, head_width=0.15, head_length=0.15,
                fc='green', ec='green', linewidth=2)
        ax.arrow(4.5, 2.5, 1, 0, head_width=0.15, head_length=0.15,
                fc='orange', ec='orange', linewidth=2)

        # Phase labels
        ax.text(5.2, 3.7, 'Phase A', fontsize=8, color='blue', fontweight='bold')
        ax.text(5.2, 3.2, 'Phase B', fontsize=8, color='green', fontweight='bold')
        ax.text(5.2, 2.7, 'Phase C', fontsize=8, color='orange', fontweight='bold')

        # Display key parameters
        info_text = f"Current: {results['I']:.2f} A\n"
        info_text += f"EMF: {results['EMF_LL']:.1f} V\n"
        info_text += f"Te: {results['Te']:.2f} Nm"
        ax.text(8.5, 4.5, info_text, fontsize=9, bbox=dict(boxstyle='round',
                facecolor='wheat', alpha=0.8))

    def plot_voltage_waveform(self, ax, Vdc, results, speed):
        """Plot voltage waveforms"""
        t, vll, current, emf, T = self.generate_waveforms(Vdc, results['I'],
                                                          results['EMF_LL'], speed)

        # Convert time to milliseconds
        t_ms = t * 1000

        ax.plot(t_ms, vll, 'b-', linewidth=2, label='Line-to-Line Voltage')
        ax.plot(t_ms, emf, 'r--', linewidth=2, label='Back EMF')
        ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Time (ms)', fontweight='bold')
        ax.set_ylabel('Voltage (V)', fontweight='bold')
        ax.set_title('Voltage Waveforms', fontweight='bold')
        ax.legend(loc='upper right')
        ax.set_xlim(0, 2*T*1000)

    def plot_current_waveform(self, ax, results, speed):
        """Plot current waveform"""
        fe = speed * self.poles / 120
        T = 1 / fe
        t = np.linspace(0, 2*T, 1000)
        t_ms = t * 1000

        # Simplified constant current during conduction
        current = np.ones_like(t) * results['I']

        ax.plot(t_ms, current, 'g-', linewidth=2, label='Phase Current')
        ax.axhline(y=results['I'], color='r', linestyle='--',
                  linewidth=1, alpha=0.5, label=f"Avg: {results['I']:.2f} A")
        ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Time (ms)', fontweight='bold')
        ax.set_ylabel('Current (A)', fontweight='bold')
        ax.set_title('Current Waveform', fontweight='bold')
        ax.legend(loc='upper right')
        ax.set_xlim(0, 2*T*1000)

    def plot_power_flow(self, ax, results):
        """Plot power flow diagram"""
        powers = [results['Pin']/1000, results['Pem']/1000, results['Pshaft']/1000]
        labels = ['Input\nPower', 'Electromagnetic\nPower', 'Shaft\nPower']
        colors = ['#ff9999', '#66b3ff', '#99ff99']

        bars = ax.barh(labels, powers, color=colors, edgecolor='black', linewidth=2)

        # Add value labels
        for i, (bar, power) in enumerate(zip(bars, powers)):
            ax.text(power + max(powers)*0.02, i, f'{power:.2f} kW',
                   va='center', fontweight='bold', fontsize=9)

        # Show losses
        loss_power = results['Pcu']/1000
        ax.text(max(powers)*0.5, 2.5, f'Copper Losses: {loss_power:.2f} kW',
               ha='center', fontsize=10, bbox=dict(boxstyle='round',
               facecolor='yellow', alpha=0.7), fontweight='bold')

        ax.set_xlabel('Power (kW)', fontweight='bold')
        ax.set_title('Power Flow', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')

    def plot_torque_info(self, ax, results):
        """Plot torque information"""
        torques = [results['Te'], results['Tshaft']]
        labels = ['Electromagnetic\nTorque', 'Shaft\nTorque']
        colors = ['#ff6b6b', '#4ecdc4']

        bars = ax.bar(labels, torques, color=colors, edgecolor='black',
                     linewidth=2, width=0.6)

        # Add value labels
        for bar, torque in zip(bars, torques):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{torque:.2f} Nm',
                   ha='center', va='bottom', fontweight='bold', fontsize=10)

        ax.set_ylabel('Torque (Nm)', fontweight='bold')
        ax.set_title('Torque Analysis', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(0, max(torques) * 1.2)

    def plot_speed_curve(self, ax, Vdc, R1L, kE, kT, current_speed):
        """Plot torque vs speed characteristic"""
        speeds = np.linspace(100, 10000, 100)
        torques = []

        for speed in speeds:
            results = self.calculate(Vdc, R1L, self.L1L, kE, kT, speed)
            torques.append(results['Te'])

        ax.plot(speeds, torques, 'b-', linewidth=2, label='Torque-Speed Curve')
        ax.plot(current_speed, self.calculate(Vdc, R1L, self.L1L, kE, kT,
                current_speed)['Te'], 'ro', markersize=10,
                label='Operating Point')
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Speed (rpm)', fontweight='bold')
        ax.set_ylabel('Torque (Nm)', fontweight='bold')
        ax.set_title('Torque-Speed Characteristic', fontweight='bold')
        ax.legend()

    def plot_efficiency(self, ax, Vdc, R1L, kE, kT, current_speed):
        """Plot efficiency vs speed"""
        speeds = np.linspace(1000, 10000, 100)
        efficiencies = []

        for speed in speeds:
            results = self.calculate(Vdc, R1L, self.L1L, kE, kT, speed)
            efficiencies.append(results['efficiency'])

        ax.plot(speeds, efficiencies, 'g-', linewidth=2, label='Efficiency')
        current_eff = self.calculate(Vdc, R1L, self.L1L, kE, kT,
                                     current_speed)['efficiency']
        ax.plot(current_speed, current_eff, 'ro', markersize=10,
               label=f'Current: {current_eff:.1f}%')
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Speed (rpm)', fontweight='bold')
        ax.set_ylabel('Efficiency (%)', fontweight='bold')
        ax.set_title('Efficiency vs Speed', fontweight='bold')
        ax.legend()
        ax.set_ylim(0, 100)

    def plot_losses(self, ax, results):
        """Plot loss breakdown"""
        losses = [results['Pcu']/1000]
        labels = ['Copper\nLosses']
        colors = ['#ff6b6b']
        explode = [0.1]

        wedges, texts, autotexts = ax.pie(losses, labels=labels, colors=colors,
                                          autopct='%1.1f%%', startangle=90,
                                          explode=explode, textprops={'fontweight': 'bold'})

        ax.set_title(f'Loss Breakdown\nTotal: {results["Pcu"]/1000:.2f} kW',
                    fontweight='bold')

        # Add legend with absolute values
        legend_labels = [f'{label}: {loss:.2f} kW'
                        for label, loss in zip(labels, losses)]
        ax.legend(legend_labels, loc='upper left', bbox_to_anchor=(0.8, 0, 0.5, 1))

def main():
    """Main function to run the simulation"""
    print("="*60)
    print("PMBM Six-Pulse Inverter Simulation")
    print("="*60)
    print("\nInitial Parameters:")
    print(f"  - DC Bus Voltage (Vdc): 600 V")
    print(f"  - Line-to-Line Resistance (R1L): 0.9 Ω")
    print(f"  - Line-to-Line Inductance (L1L): 5.0 mH")
    print(f"  - EMF Constant (kE): 0.072 V/rpm")
    print(f"  - Torque Constant (kT): 0.83 Nm/A")
    print(f"  - Motor Speed: 6000 rpm")
    print(f"  - Number of Poles: 8")
    print("\n" + "="*60)

    # Create simulation instance
    sim = PMBMInverterSimulation()

    # Calculate initial results
    results = sim.calculate(sim.Vdc, sim.R1L, sim.L1L, sim.kE, sim.kT, sim.speed)

    print("\nCalculated Results:")
    print(f"  - Line Current: {results['I']:.2f} A")
    print(f"  - Electromagnetic Torque: {results['Te']:.2f} Nm")
    print(f"  - Shaft Torque: {results['Tshaft']:.2f} Nm")
    print(f"  - Copper Losses: {results['Pcu']/1000:.2f} kW")
    print(f"  - Input Power: {results['Pin']/1000:.2f} kW")
    print(f"  - Shaft Power: {results['Pshaft']/1000:.2f} kW")
    print(f"  - Efficiency: {results['efficiency']:.2f} %")
    print("\n" + "="*60)
    print("\nUse the sliders to adjust parameters and see real-time updates!")
    print("="*60 + "\n")

    # Create interactive visualization
    sim.create_visualization()

if __name__ == "__main__":
    main()
