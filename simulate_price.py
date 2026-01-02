#!/usr/bin/env python
"""
Price Simulation Script

Simulates the impact of price changes on demand and revenue using
calculated price elasticities. Implements Feature F3 (Price Simulator)
from the project specification.

Usage:
    python simulate_price.py 22086 --change 10
    python simulate_price.py 21232 --change -5 --url http://localhost:8000
    python simulate_price.py 84879 --scenarios -10 -5 0 5 10 15 20
"""
import argparse
import sys
from typing import List, Dict, Any

import httpx


class PriceSimulator:
    """Simulates price changes and their impact on sales and revenue."""

    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Initialize simulator.
        
        Args:
            api_url: Base URL of the ElastiCom API
        """
        self.api_url = api_url

    def get_product_elasticity(self, stock_code: str) -> Dict[str, Any]:
        """
        Get elasticity data for a specific product.
        
        Args:
            stock_code: Product SKU
            
        Returns:
            Product elasticity data
            
        Raises:
            ValueError: If product not found or has insufficient data
        """
        endpoint = f"{self.api_url}/api/elasticity"
        params = {"stock_codes": [stock_code]}
        
        with httpx.Client(timeout=30) as client:
            response = client.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
        
        results = data.get("results", [])
        
        if not results:
            raise ValueError(
                f"Produkt {stock_code} nicht gefunden oder unzureichende Daten "
                "für Elastizitätsberechnung. Mindestens 3 verschiedene Preis-Mengen-Paare benötigt."
            )
        
        return results[0]

    def simulate_price_change(
        self,
        elasticity: float,
        current_price: float,
        price_change_percent: float,
        baseline_quantity: int,
    ) -> Dict[str, Any]:
        """
        Simulate impact of a price change.
        
        Based on elasticity formula:
        %ΔQ = ε × %ΔP
        
        Where:
        - %ΔQ: Percentage change in quantity demanded
        - ε: Price elasticity coefficient
        - %ΔP: Percentage change in price
        
        Args:
            elasticity: Price elasticity coefficient
            current_price: Current average price
            price_change_percent: Price change in percent
            baseline_quantity: Historical baseline quantity
            
        Returns:
            Simulation results
        """
        # Calculate quantity change based on elasticity
        quantity_change_percent = elasticity * price_change_percent
        
        # Calculate new values
        new_price = current_price * (1 + price_change_percent / 100)
        new_quantity = baseline_quantity * (1 + quantity_change_percent / 100)
        quantity_change = new_quantity - baseline_quantity
        
        # Revenue calculations
        baseline_revenue = current_price * baseline_quantity
        new_revenue = new_price * new_quantity
        revenue_change = new_revenue - baseline_revenue
        revenue_change_percent = (revenue_change / baseline_revenue) * 100 if baseline_revenue > 0 else 0
        
        return {
            "price_change_percent": round(price_change_percent, 2),
            "new_price": round(new_price, 2),
            "price_change_absolute": round(new_price - current_price, 2),
            "quantity_change_percent": round(quantity_change_percent, 2),
            "new_quantity": int(round(new_quantity)),
            "quantity_change_absolute": int(round(quantity_change)),
            "baseline_revenue": round(baseline_revenue, 2),
            "new_revenue": round(new_revenue, 2),
            "revenue_change": round(revenue_change, 2),
            "revenue_change_percent": round(revenue_change_percent, 2),
        }

    def simulate_scenarios(
        self,
        product_data: Dict[str, Any],
        scenarios: List[float],
    ) -> List[Dict[str, Any]]:
        """
        Simulate multiple price change scenarios.
        
        Args:
            product_data: Product elasticity data
            scenarios: List of price change percentages to test
            
        Returns:
            List of simulation results for each scenario
        """
        results = []
        
        for price_change in scenarios:
            simulation = self.simulate_price_change(
                elasticity=product_data["elasticity"],
                current_price=product_data["avg_price"],
                price_change_percent=price_change,
                baseline_quantity=product_data["total_quantity"],
            )
            results.append(simulation)
        
        return results

    def format_simulation_report(
        self,
        product_data: Dict[str, Any],
        simulation: Dict[str, Any],
    ) -> str:
        """
        Format simulation results as readable report.
        
        Args:
            product_data: Product elasticity data
            simulation: Simulation results
            
        Returns:
            Formatted report string
        """
        report = []
        
        # Header
        report.append("=" * 80)
        report.append("PREIS-SIMULATIONS-BERICHT")
        report.append("=" * 80)
        
        # Product info
        report.append(f"\nProdukt: {product_data['stock_code']}")
        if product_data.get("description"):
            report.append(f"Beschreibung: {product_data['description']}")
        report.append(f"Elastizität: {product_data['elasticity']:.4f}")
        report.append(f"Modellgüte (R²): {product_data['r_squared']:.4f}")
        report.append(f"Datenbasis: {product_data['sample_size']} Beobachtungen")
        
        # Interpretation
        if product_data['elasticity'] < -1.0:
            elasticity_type = "ELASTISCH (preissensitiv)"
            warning = "⚠️  Vorsicht: Starke Mengenreaktion bei Preisänderungen!"
        else:
            elasticity_type = "UNELASTISCH (weniger preissensitiv)"
            warning = "✅ Preiserhöhungen haben moderate Mengeneffekte"
        
        report.append(f"\nNachfrageverhalten: {elasticity_type}")
        report.append(warning)
        
        # Current state
        report.append("\n" + "-" * 80)
        report.append("AUSGANGSLAGE")
        report.append("-" * 80)
        report.append(f"Aktueller Durchschnittspreis: €{product_data['avg_price']:.2f}")
        report.append(f"Historisch verkaufte Menge: {product_data['total_quantity']:,} Einheiten")
        report.append(f"Bisheriger Umsatz: €{simulation['baseline_revenue']:,.2f}")
        
        # Simulation
        report.append("\n" + "-" * 80)
        report.append("SIMULATION")
        report.append("-" * 80)
        
        price_symbol = "📈" if simulation['price_change_percent'] > 0 else "📉"
        report.append(f"\n{price_symbol} Preisänderung: {simulation['price_change_percent']:+.1f}%")
        report.append(f"   Neuer Preis: €{simulation['new_price']:.2f} ({simulation['price_change_absolute']:+.2f})")
        
        quantity_symbol = "📉" if simulation['quantity_change_percent'] < 0 else "📈"
        report.append(f"\n{quantity_symbol} Erwartete Mengenänderung: {simulation['quantity_change_percent']:+.1f}%")
        report.append(f"   Neue Menge: {simulation['new_quantity']:,} Einheiten ({simulation['quantity_change_absolute']:+,})")
        
        revenue_symbol = "💰" if simulation['revenue_change'] > 0 else "💸"
        report.append(f"\n{revenue_symbol} Umsatzeffekt:")
        report.append(f"   Neuer Umsatz: €{simulation['new_revenue']:,.2f}")
        report.append(f"   Änderung: €{simulation['revenue_change']:+,.2f} ({simulation['revenue_change_percent']:+.1f}%)")
        
        # Recommendation
        report.append("\n" + "-" * 80)
        report.append("EMPFEHLUNG")
        report.append("-" * 80)
        
        if simulation['revenue_change'] > 0:
            if simulation['price_change_percent'] > 0:
                report.append("✅ PREISERHÖHUNG EMPFOHLEN")
                report.append(f"   Erwarteter Mehrerlös: €{simulation['revenue_change']:,.2f}")
            else:
                report.append("✅ PREISSENKUNG EMPFOHLEN")
                report.append(f"   Erwarteter Mehrerlös durch Volumen: €{simulation['revenue_change']:,.2f}")
        else:
            if simulation['price_change_percent'] > 0:
                report.append("❌ PREISERHÖHUNG NICHT EMPFOHLEN")
                report.append(f"   Erwarteter Umsatzverlust: €{abs(simulation['revenue_change']):,.2f}")
            else:
                report.append("❌ PREISSENKUNG NICHT EMPFOHLEN")
                report.append(f"   Erwarteter Umsatzverlust: €{abs(simulation['revenue_change']):,.2f}")
        
        # Confidence note
        report.append("\n" + "-" * 80)
        report.append("HINWEISE")
        report.append("-" * 80)
        
        if product_data['r_squared'] >= 0.7:
            report.append("✅ Hohe Modellgüte - Prognose ist zuverlässig")
        elif product_data['r_squared'] >= 0.4:
            report.append("⚠️  Mittlere Modellgüte - Prognose mit Vorsicht interpretieren")
        else:
            report.append("❌ Niedrige Modellgüte - Prognose unsicher, mehr Daten empfohlen")
        
        report.append("\nMethodologie:")
        report.append("  • Elastizitätsberechnung: Log-log Regression (Paczkowski, 2018)")
        report.append("  • Nachfrageänderung: %ΔQ = ε × %ΔP")
        report.append("  • Annahme: Ceteris paribus (alle anderen Faktoren konstant)")
        
        report.append("=" * 80)
        
        return "\n".join(report)

    def format_scenario_comparison(
        self,
        product_data: Dict[str, Any],
        scenarios: List[Dict[str, Any]],
    ) -> str:
        """
        Format multiple scenarios as comparison table.
        
        Args:
            product_data: Product elasticity data
            scenarios: List of simulation results
            
        Returns:
            Formatted comparison table
        """
        report = []
        
        # Header
        report.append("=" * 100)
        report.append("PREIS-SZENARIO-VERGLEICH")
        report.append("=" * 100)
        report.append(f"\nProdukt: {product_data['stock_code']} - {product_data.get('description', 'N/A')}")
        report.append(f"Elastizität: {product_data['elasticity']:.4f} | R²: {product_data['r_squared']:.4f}")
        report.append(f"Baseline: €{product_data['avg_price']:.2f} × {product_data['total_quantity']:,} = €{product_data['avg_price'] * product_data['total_quantity']:,.2f}")
        
        # Table header
        report.append("\n" + "-" * 100)
        header = (
            f"{'Preis-Δ':>10} | {'Neuer Preis':>12} | {'Mengen-Δ':>12} | "
            f"{'Neue Menge':>13} | {'Umsatz-Δ':>13} | {'Neuer Umsatz':>15}"
        )
        report.append(header)
        report.append("-" * 100)
        
        # Find best scenario
        best_scenario = max(scenarios, key=lambda x: x['new_revenue'])
        
        # Table rows
        for sim in scenarios:
            is_best = sim['price_change_percent'] == best_scenario['price_change_percent']
            marker = "→" if is_best else " "
            
            row = (
                f"{marker} {sim['price_change_percent']:+6.1f}% | "
                f"€{sim['new_price']:>10.2f} | "
                f"{sim['quantity_change_percent']:+10.1f}% | "
                f"{sim['new_quantity']:>12,} | "
                f"{sim['revenue_change_percent']:+11.1f}% | "
                f"€{sim['new_revenue']:>13,.2f}"
            )
            report.append(row)
        
        report.append("-" * 100)
        
        # Best scenario highlight
        report.append(f"\n💰 OPTIMALES SZENARIO: {best_scenario['price_change_percent']:+.1f}% Preisänderung")
        report.append(f"   Erwarteter Umsatz: €{best_scenario['new_revenue']:,.2f}")
        report.append(f"   Verbesserung: €{best_scenario['revenue_change']:+,.2f} ({best_scenario['revenue_change_percent']:+.1f}%)")
        
        report.append("=" * 100)
        
        return "\n".join(report)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Simulate price changes and their impact on demand and revenue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "stock_code",
        type=str,
        help="Product SKU to simulate"
    )
    
    parser.add_argument(
        "--change",
        type=float,
        help="Single price change percentage to simulate (e.g., 10 for +10%%)"
    )
    
    parser.add_argument(
        "--scenarios",
        nargs="+",
        type=float,
        help="Multiple price change scenarios to compare"
    )
    
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="Base API URL (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    if not args.change and not args.scenarios:
        print("❌ Fehler: Entweder --change oder --scenarios muss angegeben werden", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    
    simulator = PriceSimulator(api_url=args.url)
    
    print(f"🔍 Lade Elastizitätsdaten für {args.stock_code}...")
    
    try:
        product_data = simulator.get_product_elasticity(args.stock_code)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPError as e:
        print(f"❌ API-Fehler: {e}", file=sys.stderr)
        sys.exit(1)
    
    if args.change is not None:
        # Single simulation
        simulation = simulator.simulate_price_change(
            elasticity=product_data["elasticity"],
            current_price=product_data["avg_price"],
            price_change_percent=args.change,
            baseline_quantity=product_data["total_quantity"],
        )
        
        report = simulator.format_simulation_report(product_data, simulation)
        print(report)
    
    else:
        # Multiple scenarios
        scenarios = simulator.simulate_scenarios(product_data, args.scenarios)
        report = simulator.format_scenario_comparison(product_data, scenarios)
        print(report)


if __name__ == "__main__":
    main()
