#!/usr/bin/env python
"""
Elasticity Analysis Script

Analyzes price elasticity data and provides actionable pricing recommendations
for e-commerce managers based on Nagle et al. (2016) pricing strategies.

Usage:
    python analyze_elasticity.py --url http://localhost:8000
    python analyze_elasticity.py --stock-codes 22086 21232
    python analyze_elasticity.py --country "United Kingdom"
    python analyze_elasticity.py --output analysis_report.json
"""
import argparse
import json
import sys
from datetime import date
from typing import List, Dict, Any, Optional

import httpx


# Elasticity thresholds based on pricing literature (Nagle et al., 2016)
HIGHLY_ELASTIC_THRESHOLD = -1.5  # Very price-sensitive
ELASTIC_THRESHOLD = -1.0         # Price-sensitive
UNELASTIC_THRESHOLD = -0.5       # Less price-sensitive
HIGHLY_UNELASTIC_THRESHOLD = -0.2  # Very insensitive

# R² thresholds for reliability
HIGH_CONFIDENCE = 0.7
MEDIUM_CONFIDENCE = 0.4


class ElasticityAnalyzer:
    """Analyzer for price elasticity data with strategic recommendations."""

    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Initialize analyzer.
        
        Args:
            api_url: Base URL of the ElastiCom API
        """
        self.api_url = api_url

    def fetch_elasticity_data(
        self,
        stock_codes: Optional[List[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        country: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch elasticity data from API.
        
        Args:
            stock_codes: Optional list of product SKUs
            start_date: Start of analysis period
            end_date: End of analysis period
            country: Filter by country
            
        Returns:
            API response dictionary
        """
        endpoint = f"{self.api_url}/api/elasticity"
        params = {}
        
        if stock_codes:
            params["stock_codes"] = stock_codes
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        if country:
            params["country"] = country
        
        with httpx.Client(timeout=60) as client:
            response = client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()

    def classify_elasticity(self, elasticity: float) -> Dict[str, Any]:
        """
        Classify product by elasticity type.
        
        Based on Paczkowski (2018) and Nagle et al. (2016).
        
        Args:
            elasticity: Price elasticity coefficient
            
        Returns:
            Classification with category, interpretation, and strategy
        """
        if elasticity < HIGHLY_ELASTIC_THRESHOLD:
            return {
                "category": "Hochelastisch",
                "sensitivity": "Sehr hohe Preissensitivität",
                "interpretation": "Kunden reagieren stark auf Preisänderungen",
                "strategy": "Volumenstrategie: Niedrige Preise, hohe Mengen",
                "action": "NICHT erhöhen",
                "color": "🔴",
            }
        elif elasticity < ELASTIC_THRESHOLD:
            return {
                "category": "Elastisch",
                "sensitivity": "Hohe Preissensitivität",
                "interpretation": "Nachfrage ist deutlich preisabhängig",
                "strategy": "Wettbewerbspreisstrategie mit Fokus auf Marktanteil",
                "action": "Vorsichtig anpassen",
                "color": "🟠",
            }
        elif elasticity < UNELASTIC_THRESHOLD:
            return {
                "category": "Moderat unelastisch",
                "sensitivity": "Mittlere Preissensitivität",
                "interpretation": "Nachfrage reagiert moderat auf Preis",
                "strategy": "Balanced Pricing: Optimierung zwischen Marge und Volumen",
                "action": "Optimierungspotenzial",
                "color": "🟡",
            }
        elif elasticity < HIGHLY_UNELASTIC_THRESHOLD:
            return {
                "category": "Unelastisch",
                "sensitivity": "Geringe Preissensitivität",
                "interpretation": "Kunden kaufen relativ preisunabhängig",
                "strategy": "Premium-Pricing: Höhere Preise, höhere Margen",
                "action": "Preis ERHÖHEN möglich",
                "color": "🟢",
            }
        else:
            return {
                "category": "Hochgradig unelastisch",
                "sensitivity": "Sehr geringe Preissensitivität",
                "interpretation": "Preis spielt untergeordnete Rolle",
                "strategy": "Value-Based Pricing: Nutzenorientierte Preisbildung",
                "action": "Deutlich ERHÖHEN möglich",
                "color": "💎",
            }

    def assess_confidence(self, r_squared: float) -> Dict[str, str]:
        """
        Assess confidence level of elasticity estimate.
        
        Args:
            r_squared: R² value from regression
            
        Returns:
            Confidence assessment
        """
        if r_squared >= HIGH_CONFIDENCE:
            return {
                "level": "Hoch",
                "reliability": "Sehr zuverlässig",
                "recommendation": "Daten sind aussagekräftig für Preisentscheidungen",
                "symbol": "✅",
            }
        elif r_squared >= MEDIUM_CONFIDENCE:
            return {
                "level": "Mittel",
                "reliability": "Moderat zuverlässig",
                "recommendation": "Mit Vorsicht verwenden, weitere Daten sammeln",
                "symbol": "⚠️",
            }
        else:
            return {
                "level": "Niedrig",
                "reliability": "Wenig zuverlässig",
                "recommendation": "Nicht für Preisentscheidungen nutzen, mehr Daten benötigt",
                "symbol": "❌",
            }

    def calculate_price_change_impact(
        self,
        elasticity: float,
        current_price: float,
        price_change_percent: float,
        total_quantity: int,
    ) -> Dict[str, Any]:
        """
        Simulate impact of price change on demand and revenue.
        
        Based on elasticity formula: %ΔQ = ε × %ΔP
        
        Args:
            elasticity: Price elasticity coefficient
            current_price: Current average price
            price_change_percent: Price change in percent (e.g., 10 for +10%)
            total_quantity: Historical total quantity sold
            
        Returns:
            Impact simulation results
        """
        # Calculate quantity change: %ΔQ = ε × %ΔP
        quantity_change_percent = elasticity * price_change_percent
        
        # New values
        new_price = current_price * (1 + price_change_percent / 100)
        new_quantity = total_quantity * (1 + quantity_change_percent / 100)
        
        # Revenue calculation
        old_revenue = current_price * total_quantity
        new_revenue = new_price * new_quantity
        revenue_change = new_revenue - old_revenue
        revenue_change_percent = (revenue_change / old_revenue) * 100
        
        return {
            "price_change_percent": round(price_change_percent, 2),
            "new_price": round(new_price, 2),
            "quantity_change_percent": round(quantity_change_percent, 2),
            "new_quantity": int(new_quantity),
            "old_revenue": round(old_revenue, 2),
            "new_revenue": round(new_revenue, 2),
            "revenue_change": round(revenue_change, 2),
            "revenue_change_percent": round(revenue_change_percent, 2),
        }

    def find_optimal_price_point(
        self,
        elasticity: float,
        current_price: float,
        total_quantity: int,
        min_change: float = -50,
        max_change: float = 50,
        step: float = 5,
    ) -> Dict[str, Any]:
        """
        Find price point that maximizes revenue.
        
        Note: This is a simplified model. In reality, costs, competition,
        and other factors must be considered.
        
        Args:
            elasticity: Price elasticity coefficient
            current_price: Current average price
            total_quantity: Historical total quantity
            min_change: Minimum price change to test (%)
            max_change: Maximum price change to test (%)
            step: Step size for testing (%)
            
        Returns:
            Optimal price point analysis
        """
        best_revenue = current_price * total_quantity
        best_price_change = 0
        results = []
        
        # Test different price points
        price_change = min_change
        while price_change <= max_change:
            impact = self.calculate_price_change_impact(
                elasticity, current_price, price_change, total_quantity
            )
            
            results.append({
                "price_change": price_change,
                "revenue": impact["new_revenue"],
            })
            
            if impact["new_revenue"] > best_revenue:
                best_revenue = impact["new_revenue"]
                best_price_change = price_change
            
            price_change += step
        
        optimal_impact = self.calculate_price_change_impact(
            elasticity, current_price, best_price_change, total_quantity
        )
        
        return {
            "optimal_price_change_percent": best_price_change,
            "optimal_price": optimal_impact["new_price"],
            "expected_quantity": optimal_impact["new_quantity"],
            "expected_revenue": optimal_impact["new_revenue"],
            "revenue_improvement": round(best_revenue - (current_price * total_quantity), 2),
            "improvement_percent": round(
                ((best_revenue / (current_price * total_quantity)) - 1) * 100, 2
            ),
            "tested_range": f"{min_change}% bis {max_change}%",
        }

    def segment_products(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """
        Segment products into strategic pricing categories.
        
        Creates segments for portfolio-based pricing strategies
        (Nagle et al., 2016, Chapter 9).
        
        Args:
            results: List of elasticity results from API
            
        Returns:
            Dictionary with product segments
        """
        segments = {
            "premium_candidates": [],      # Unelastic, high confidence
            "volume_drivers": [],          # Elastic, high confidence
            "optimization_targets": [],    # Moderate elasticity
            "data_insufficient": [],       # Low confidence
        }
        
        for result in results:
            elasticity = result["elasticity"]
            r_squared = result["r_squared"]
            
            if r_squared < MEDIUM_CONFIDENCE:
                segments["data_insufficient"].append(result)
            elif elasticity < ELASTIC_THRESHOLD:
                segments["volume_drivers"].append(result)
            elif elasticity > UNELASTIC_THRESHOLD:
                segments["premium_candidates"].append(result)
            else:
                segments["optimization_targets"].append(result)
        
        return segments

    def generate_report(self, data: Dict[str, Any]) -> str:
        """
        Generate comprehensive analysis report.
        
        Args:
            data: Elasticity data from API
            
        Returns:
            Formatted report string
        """
        results = data.get("results", [])
        meta = data.get("meta", {})
        
        if not results:
            return "❌ Keine Elastizitätsdaten verfügbar. Prüfen Sie die Datenbasis."
        
        # Header
        report = []
        report.append("=" * 80)
        report.append("PREISELASTIZITÄTS-ANALYSE")
        report.append("=" * 80)
        report.append(f"Zeitraum: {meta.get('start_date')} bis {meta.get('end_date')}")
        report.append(f"Analysierte Produkte: {meta.get('total_products')}")
        report.append("=" * 80)
        report.append("")
        
        # Segment analysis
        segments = self.segment_products(results)
        
        report.append("📊 PRODUKT-SEGMENTIERUNG")
        report.append("-" * 80)
        report.append(f"Premium-Kandidaten (Preiserhöhung möglich): {len(segments['premium_candidates'])}")
        report.append(f"Volumentreiber (Niedrigpreisstrategie): {len(segments['volume_drivers'])}")
        report.append(f"Optimierungsziele (Balanced Pricing): {len(segments['optimization_targets'])}")
        report.append(f"Unzureichende Daten: {len(segments['data_insufficient'])}")
        report.append("")
        
        # Top opportunities
        report.append("💰 TOP PREISERHÖHUNGS-KANDIDATEN")
        report.append("-" * 80)
        premium_sorted = sorted(
            segments["premium_candidates"],
            key=lambda x: x["elasticity"],
            reverse=True
        )[:5]
        
        for i, product in enumerate(premium_sorted, 1):
            classification = self.classify_elasticity(product["elasticity"])
            confidence = self.assess_confidence(product["r_squared"])
            
            report.append(f"\n{i}. {classification['color']} {product['stock_code']} - {product.get('description', 'N/A')}")
            report.append(f"   Elastizität: {product['elasticity']:.4f} ({classification['category']})")
            report.append(f"   Zuverlässigkeit: R² = {product['r_squared']:.4f} {confidence['symbol']}")
            report.append(f"   Ø Preis: €{product['avg_price']:.2f} | Verkaufte Menge: {product['total_quantity']:,}")
            report.append(f"   💡 Strategie: {classification['strategy']}")
            
            # Simulate +10% price increase
            impact = self.calculate_price_change_impact(
                product["elasticity"],
                product["avg_price"],
                10,
                product["total_quantity"]
            )
            report.append(f"   📈 Bei +10% Preis: {impact['quantity_change_percent']:.1f}% Mengenänderung")
            report.append(f"      → Umsatzänderung: €{impact['revenue_change']:,.2f} ({impact['revenue_change_percent']:+.1f}%)")
        
        report.append("")
        
        # Volume drivers
        report.append("🎯 TOP VOLUMENTREIBER")
        report.append("-" * 80)
        volume_sorted = sorted(
            segments["volume_drivers"],
            key=lambda x: x["elasticity"]
        )[:5]
        
        for i, product in enumerate(volume_sorted, 1):
            classification = self.classify_elasticity(product["elasticity"])
            confidence = self.assess_confidence(product["r_squared"])
            
            report.append(f"\n{i}. {classification['color']} {product['stock_code']} - {product.get('description', 'N/A')}")
            report.append(f"   Elastizität: {product['elasticity']:.4f} ({classification['category']})")
            report.append(f"   Zuverlässigkeit: R² = {product['r_squared']:.4f} {confidence['symbol']}")
            report.append(f"   Ø Preis: €{product['avg_price']:.2f} | Verkaufte Menge: {product['total_quantity']:,}")
            report.append(f"   ⚠️  Warnung: {classification['strategy']}")
            
            # Simulate -5% price decrease for volume
            impact = self.calculate_price_change_impact(
                product["elasticity"],
                product["avg_price"],
                -5,
                product["total_quantity"]
            )
            report.append(f"   📉 Bei -5% Preis: {impact['quantity_change_percent']:.1f}% Mengenänderung")
            report.append(f"      → Umsatzänderung: €{impact['revenue_change']:,.2f} ({impact['revenue_change_percent']:+.1f}%)")
        
        report.append("")
        
        # Statistical summary
        report.append("📈 STATISTIK-ÜBERSICHT")
        report.append("-" * 80)
        
        elasticities = [r["elasticity"] for r in results]
        r_squareds = [r["r_squared"] for r in results]
        
        report.append(f"Durchschnittliche Elastizität: {sum(elasticities) / len(elasticities):.4f}")
        report.append(f"Median Elastizität: {sorted(elasticities)[len(elasticities)//2]:.4f}")
        report.append(f"Durchschnittliches R²: {sum(r_squareds) / len(r_squareds):.4f}")
        report.append(f"Produkte mit R² > 0.7: {sum(1 for r in r_squareds if r > 0.7)}")
        
        report.append("")
        report.append("=" * 80)
        report.append("📚 METHODOLOGIE")
        report.append("-" * 80)
        report.append("Berechnung: Log-log Regression ln(Q) = α + ε × ln(P)")
        report.append("Literatur: Paczkowski (2018), Nagle et al. (2016)")
        report.append("Interpretation:")
        report.append("  • ε < -1.0: Elastische Nachfrage (preissensitiv)")
        report.append("  • ε > -1.0: Unelastische Nachfrage (weniger preissensitiv)")
        report.append("  • R² > 0.7: Hohe Modellgüte (zuverlässig)")
        report.append("=" * 80)
        
        return "\n".join(report)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze price elasticity data and generate pricing recommendations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="Base API URL (default: http://localhost:8000)"
    )
    
    parser.add_argument(
        "--stock-codes",
        nargs="+",
        help="Filter by specific product SKUs"
    )
    
    parser.add_argument(
        "--country",
        type=str,
        help="Filter by country"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Save report to JSON file"
    )
    
    args = parser.parse_args()
    
    analyzer = ElasticityAnalyzer(api_url=args.url)
    
    print("🔍 Lade Elastizitätsdaten...")
    
    try:
        data = analyzer.fetch_elasticity_data(
            stock_codes=args.stock_codes,
            country=args.country,
        )
    except httpx.HTTPError as e:
        print(f"❌ Fehler beim Laden der Daten: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Generate and print report
    report = analyzer.generate_report(data)
    print(report)
    
    # Save to file if requested
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Daten gespeichert in: {args.output}")


if __name__ == "__main__":
    main()
