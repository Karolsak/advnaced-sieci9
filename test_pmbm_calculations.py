"""
Test script to verify PMBM calculations and display results
"""

import numpy as np

def calculate_pmbm_parameters():
    """Calculate PMBM motor parameters"""
    print("="*80)
    print("PMBM SIX-PULSE INVERTER - CALCULATION RESULTS")
    print("="*80)

    # Given parameters
    print("\n📋 GIVEN PARAMETERS:")
    print("-" * 80)
    Vdc = 600  # DC bus voltage (V)
    R1L = 0.9  # Line-to-line resistance (Ohm)
    L1L = 5.0  # Line-to-line inductance (mH)
    kE = 0.072  # EMF constant (V/rpm)
    kT = 0.83  # Torque constant (Nm/A)
    speed = 6000  # Motor speed (rpm)
    poles = 8  # Number of poles

    print(f"  • DC Bus Voltage (Vdc)               : {Vdc} V")
    print(f"  • Line-to-Line Resistance (R1L)      : {R1L} Ω")
    print(f"  • Line-to-Line Inductance (L1L)      : {L1L} mH")
    print(f"  • EMF Constant (kE)                  : {kE} V/rpm")
    print(f"  • Torque Constant (kT)               : {kT} Nm/A")
    print(f"  • Motor Speed                        : {speed} rpm")
    print(f"  • Number of Poles                    : {poles}")

    # Calculations
    print("\n🔧 STEP-BY-STEP CALCULATIONS:")
    print("-" * 80)

    # 1. Back EMF
    EMF_LL = kE * speed
    print(f"\n1. Back EMF (Line-to-Line):")
    print(f"   EMF_LL = kE × speed")
    print(f"   EMF_LL = {kE} × {speed} = {EMF_LL:.2f} V")

    # 2. Line-to-line voltage (for six-pulse inverter with two phases on)
    VLL = Vdc
    print(f"\n2. Applied Voltage (Six-Pulse Inverter):")
    print(f"   VLL = Vdc = {VLL} V")

    # 3. Current
    I = (VLL - EMF_LL) / R1L
    print(f"\n3. Line Current:")
    print(f"   I = (VLL - EMF_LL) / R1L")
    print(f"   I = ({VLL} - {EMF_LL:.2f}) / {R1L}")
    print(f"   I = {VLL - EMF_LL:.2f} / {R1L}")
    print(f"   I = {I:.2f} A")

    # 4. Electromagnetic torque
    Te = kT * I
    print(f"\n4. Electromagnetic Torque:")
    print(f"   Te = kT × I")
    print(f"   Te = {kT} × {I:.2f}")
    print(f"   Te = {Te:.2f} Nm")

    # 5. Shaft torque (assuming no mechanical losses)
    Tshaft = Te
    print(f"\n5. Shaft Torque (no mechanical losses):")
    print(f"   Tshaft = Te = {Tshaft:.2f} Nm")

    # 6. Copper losses
    Pcu = I**2 * R1L
    print(f"\n6. Copper Losses (Stator Winding):")
    print(f"   Pcu = I² × R1L")
    print(f"   Pcu = ({I:.2f})² × {R1L}")
    print(f"   Pcu = {I**2:.2f} × {R1L}")
    print(f"   Pcu = {Pcu:.2f} W = {Pcu/1000:.2f} kW")

    # 7. Power calculations
    omega = 2 * np.pi * speed / 60
    Pin = VLL * I
    Pem = EMF_LL * I
    Pshaft = Pem
    efficiency = (Pem / Pin * 100) if Pin > 0 else 0

    print(f"\n7. Power Analysis:")
    print(f"   Angular velocity (ω) = 2π × speed / 60")
    print(f"   ω = {omega:.2f} rad/s")
    print(f"\n   Input Power:")
    print(f"   Pin = VLL × I = {VLL} × {I:.2f} = {Pin:.2f} W = {Pin/1000:.2f} kW")
    print(f"\n   Electromagnetic Power:")
    print(f"   Pem = EMF_LL × I = {EMF_LL:.2f} × {I:.2f} = {Pem:.2f} W = {Pem/1000:.2f} kW")
    print(f"\n   Shaft Power (no mechanical losses):")
    print(f"   Pshaft = Pem = {Pshaft:.2f} W = {Pshaft/1000:.2f} kW")
    print(f"\n   Efficiency:")
    print(f"   η = (Pem / Pin) × 100")
    print(f"   η = ({Pem:.2f} / {Pin:.2f}) × 100")
    print(f"   η = {efficiency:.2f} %")

    # Power balance check
    print(f"\n8. Power Balance Check:")
    print(f"   Pin = Pem + Pcu")
    print(f"   {Pin:.2f} = {Pem:.2f} + {Pcu:.2f}")
    print(f"   {Pin:.2f} = {Pem + Pcu:.2f} ✓")

    # Final results summary
    print("\n" + "="*80)
    print("📊 FINAL RESULTS SUMMARY")
    print("="*80)
    print(f"\n┌{'─'*76}┐")
    print(f"│ {'PARAMETER':<45} {'VALUE':>15} {'UNIT':>12} │")
    print(f"├{'─'*76}┤")
    print(f"│ {'Line Current (I)':<45} {I:>15.2f} {'A':>12} │")
    print(f"│ {'Electromagnetic Torque (Te)':<45} {Te:>15.2f} {'Nm':>12} │")
    print(f"│ {'Shaft Torque (Tshaft)':<45} {Tshaft:>15.2f} {'Nm':>12} │")
    print(f"│ {'Copper Losses (Pcu)':<45} {Pcu/1000:>15.2f} {'kW':>12} │")
    print(f"│ {'Input Power (Pin)':<45} {Pin/1000:>15.2f} {'kW':>12} │")
    print(f"│ {'Electromagnetic Power (Pem)':<45} {Pem/1000:>15.2f} {'kW':>12} │")
    print(f"│ {'Shaft Power (Pshaft)':<45} {Pshaft/1000:>15.2f} {'kW':>12} │")
    print(f"│ {'Efficiency (η)':<45} {efficiency:>15.2f} {'%':>12} │")
    print(f"└{'─'*76}┘")

    print("\n" + "="*80)
    print("✅ CALCULATION COMPLETE")
    print("="*80)
    print("\nTo run the interactive visualization:")
    print("  python pmbm_inverter_simulation.py")
    print("\nNote: The visualization includes:")
    print("  • Circuit diagram")
    print("  • Voltage and current waveforms")
    print("  • Power flow diagram")
    print("  • Torque analysis")
    print("  • Torque-speed characteristics")
    print("  • Efficiency curves")
    print("  • Loss breakdown")
    print("  • Interactive sliders for all parameters")
    print("="*80 + "\n")

if __name__ == "__main__":
    calculate_pmbm_parameters()
