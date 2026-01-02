#!/usr/bin/env python
"""
Product Portfolio Analysis Script

Analyzes the entire product portfolio and creates strategic segments
for portfolio-based pricing optimization (Nagle et al., 2016, Chapter 9).

This implements the foundation for the Dashboard feature (F2) with
demand segments visualization.

Usage:
    python portfolio_analysis.py
    python portfolio_analysis.py --min-rsquared 0.6
    python portfolio_analysis.py --country "United Kingdom"
    python portfolio_analysis.py --export portfolio_segments.json
"""
import argparse
import json
import sys
from typing import List, Dict, Any, Optional

import httpx


class PortfolioAnalyzer:
    """Analyzes product portfolio for strategic pricing segmentation."""

    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Initialize analyzer.
        
        Args:
            api_url: Base URL of the ElastiCom API
        """
        self.api_url = api_url

    def fetch_all_elasticities(
        self,
        country: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch elasticity data for all products.
        
        Args:
            country: Optional country filter
            
        Returns:
            API response with all elasticities
        """
        endpoint = f"{self.api_url}/api/elasticity"
        params = {}
        
        if country:
            params["country"] = country
        
        with httpx.Client(timeout=120) as client:
            response = client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()

    def create_strategic_segments(
        self,
        results: List[Dict[str, Any]],
        min_rsquared: float = 0.4,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Segment products into strategic pricing categories.
        
        Based on Boston Consulting Group (BCG) approach adapted for pricing.
        
        Segments:
        1. Premium Stars: Unelastic + high volume → Preiserhöhung
        2. Cash Cows: Unelastic + moderate volume → Stabilität
        3. Volume Champions: Elastic + high volume → Wettbewerbspreis
        4. Niche Products: Elastic + low volume → Differenzierung
        5. Question Marks: Moderate elasticity → Optimierung
        6. Data Gaps: Insufficient data quality → Monitoring
        
        Args:
            results: List of elasticity results
            min_rsquared: Minimum R² for reliable data
            
        Returns:
            Dictionary with segmented products
        """
        # Calculate volume percentiles for classification
        volumes = [r["total_quantity"] for r in results]
        volumes_sorted = sorted(volumes)
        
        if len(volumes_sorted) > 0:
            high_volume_threshold = volumes_sorted[int(len(volumes_sorted) * 0.75)]
            low_volume_threshold = volumes_sorted[int(len(volumes_sorted) * 0.25)]
        else:
            high_volume_threshold = 0
            low_volume_threshold = 0
        
        segments = {
            "premium_stars": [],       # Unelastic, high volume, high confidence
            "cash_cows": [],           # Unelastic, moderate volume
            "volume_champions": [],    # Elastic, high volume
            "niche_products": [],      # Elastic, low volume
            "question_marks": [],      # Moderate elasticity
            "data_gaps": [],           # Low confidence
        }
        
        for product in results:
            elasticity = product["elasticity"]
            r_squared = product["r_squared"]
            volume = product["total_quantity"]
            
            # First filter: data quality
            if r_squared < min_rsquared:
                segments["data_gaps"].append(product)
                continue
            
            # Classify by elasticity and volume
            is_unelastic = elasticity > -1.0
            is_elastic = elasticity < -1.5
            is_high_volume = volume >= high_volume_threshold
            is_low_volume = volume <= low_volume_threshold
            
            if is_unelastic and is_high_volume:
                segments["premium_stars"].append(product)
            elif is_unelastic and not is_high_volume:
                segments["cash_cows"].append(product)
            elif is_elastic and is_high_volume:
                segments["volume_champions"].append(product)
            elif is_elastic and is_low_volume:
                segments["niche_products"].append(product)
            else:
                segments["question_marks"].append(product)
        
        return segments

    def calculate_segment_kpis(
        self,
        segment_products: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate KPIs for a product segment.
        
        Args:
            segment_products: List of products in segment
            
        Returns:
            Segment KPIs
        """
        if not segment_products:
            return {
                "count": 0,
                "total_quantity": 0,
                "total_revenue": 0,
                "avg_price": 0,
                "avg_elasticity": 0,
                "avg_rsquared": 0,
            }
        
        total_quantity = sum(p["total_quantity"] for p in segment_products)
        total_revenue = sum(p["avg_price"] * p["total_quantity"] for p in segment_products)
        
        return {
            "count": len(segment_products),
            "total_quantity": total_quantity,
            "total_revenue": round(total_revenue, 2),
            "avg_price": round(sum(p["avg_price"] for p in segment_products) / len(segment_products), 2),
            "avg_elasticity": round(sum(p["elasticity"] for p in segment_products) / len(segment_products), 4),
            "avg_rsquared": round(sum(p["r_squared"] for p in segment_products) / len(segment_products), 4),
            "revenue_share": 0,  # Will be calculated later
        }

    def generate_portfolio_report(
        self,
        segments: Dict[str, List[Dict[str, Any]]],
    ) -> str:
        """
        Generate comprehensive portfolio analysis report.
        
        Args:
            segments: Product segments
            
        Returns:
            Formatted report
        """
        report = []
        
        # Calculate total revenue for share calculation
        all_products = []
        for products in segments.values():
            all_products.extend(products)
        
        total_revenue = sum(p["avg_price"] * p["total_quantity"] for p in all_products)
        
        # Header
        report.append("=" * 100)
        report.append("PORTFOLIO-ANALYSE: STRATEGISCHE PRODUKT-SEGMENTIERUNG")
        report.append("=" * 100)
        report.append(f"Gesamtprodukte: {len(all_products)}")
        report.append(f"Portfolio-Umsatz: €{total_revenue:,.2f}")
        report.append("=" * 100)
        report.append("")
        
        # Segment analysis
        segment_configs = [
            {
                "key": "premium_stars",
                "title": "💎 PREMIUM STARS",
                "description": "Unelastische Produkte mit hohem Volumen",
                "strategy": "PREISERHÖHUNG: Maximale Margen-Optimierung",
                "action": "Preise um 5-15% erhöhen, Premium-Positionierung stärken",
                "priority": "🔴 HOCH",
            },
            {
                "key": "cash_cows",
                "title": "🐄 CASH COWS",
                "description": "Unelastische Produkte mit moderatem Volumen",
                "strategy": "STABILITÄT: Konstante Margen sichern",
                "action": "Preise stabil halten, regelmäßige Anpassungen an Inflation",
                "priority": "🟡 MITTEL",
            },
            {
                "key": "volume_champions",
                "title": "📊 VOLUME CHAMPIONS",
                "description": "Elastische Produkte mit hohem Volumen",
                "strategy": "WETTBEWERBSPREIS: Marktanteil sichern",
                "action": "Konkurrenzmittel beobachten, keine Preiserhöhungen",
                "priority": "🟠 MITTEL-HOCH",
            },
            {
                "key": "niche_products",
                "title": "🎯 NISCHE",
                "description": "Elastische Produkte mit niedrigem Volumen",
                "strategy": "DIFFERENZIERUNG: Unique Value Proposition",
                "action": "Produktmerkmale betonen, Bundle-Angebote prüfen",
                "priority": "🟢 NIEDRIG",
            },
            {
                "key": "question_marks",
                "title": "❓ OPTIMIERUNGSZIELE",
                "description": "Moderate Elastizität - Optimierungspotenzial",
                "strategy": "TESTEN: A/B-Tests und Experimente",
                "action": "Systematische Preis-Tests durchführen",
                "priority": "🟡 MITTEL",
            },
            {
                "key": "data_gaps",
                "title": "📉 DATENLÜCKEN",
                "description": "Unzureichende Datenqualität",
                "strategy": "MONITORING: Mehr Daten sammeln",
                "action": "Preisvariationen einführen, mehr Beobachtungen sammeln",
                "priority": "⚪ NACHRANGIG",
            },
        ]
        
        for config in segment_configs:
            products = segments[config["key"]]
            kpis = self.calculate_segment_kpis(products)
            
            if total_revenue > 0:
                kpis["revenue_share"] = (kpis["total_revenue"] / total_revenue) * 100
            
            report.append(config["title"])
            report.append("-" * 100)
            report.append(f"Beschreibung: {config['description']}")
            report.append(f"Strategie: {config['strategy']}")
            report.append(f"Handlung: {config['action']}")
            report.append(f"Priorität: {config['priority']}")
            report.append("")
            report.append("KPIs:")
            report.append(f"  • Produkte: {kpis['count']}")
            report.append(f"  • Umsatzanteil: {kpis['revenue_share']:.1f}% (€{kpis['total_revenue']:,.2f})")
            report.append(f"  • Gesamtvolumen: {kpis['total_quantity']:,} Einheiten")
            report.append(f"  • Ø Preis: €{kpis['avg_price']:.2f}")
            report.append(f"  • Ø Elastizität: {kpis['avg_elasticity']:.4f}")
            report.append(f"  • Ø Modellgüte: R² = {kpis['avg_rsquared']:.4f}")
            
            # Top 3 products in segment by revenue
            if products:
                products_by_revenue = sorted(
                    products,
                    key=lambda x: x["avg_price"] * x["total_quantity"],
                    reverse=True
                )[:3]
                
                report.append("")
                report.append("  Top Produkte:")
                for i, p in enumerate(products_by_revenue, 1):
                    revenue = p["avg_price"] * p["total_quantity"]
                    report.append(
                        f"    {i}. {p['stock_code']}: €{revenue:,.2f} "
                        f"(ε={p['elasticity']:.2f}, R²={p['r_squared']:.2f})"
                    )
            
            report.append("")
            report.append("")
        
        # Strategic recommendations
        report.append("=" * 100)
        report.append("🎯 STRATEGISCHE HANDLUNGSEMPFEHLUNGEN")
        report.append("=" * 100)
        
        premium_kpis = self.calculate_segment_kpis(segments["premium_stars"])
        volume_kpis = self.calculate_segment_kpis(segments["volume_champions"])
        
        if total_revenue > 0:
            premium_kpis["revenue_share"] = (premium_kpis["total_revenue"] / total_revenue) * 100
            volume_kpis["revenue_share"] = (volume_kpis["total_revenue"] / total_revenue) * 100
        
        report.append("")
        report.append("1. SOFORTMASSNAHMEN (0-3 Monate):")
        report.append(f"   • Premium Stars ({premium_kpis['count']} Produkte, {premium_kpis['revenue_share']:.1f}% Umsatz):")
        report.append("     → Preise um durchschnittlich 10% erhöhen")
        report.append(f"     → Erwarteter Mehrumsatz: ~€{premium_kpis['total_revenue'] * 0.08:,.2f}")
        report.append("")
        report.append(f"   • Volume Champions ({volume_kpis['count']} Produkte, {volume_kpis['revenue_share']:.1f}% Umsatz):")
        report.append("     → Preise NICHT erhöhen - Marktanteil gefährdet")
        report.append("     → Stattdessen: Operational Excellence & Kostenoptimierung")
        
        report.append("")
        report.append("2. MITTELFRISTIG (3-6 Monate):")
        report.append("   • Systematische A/B-Tests bei Question Marks")
        report.append("   • Bundle-Strategien für Nischenprodukte entwickeln")
        report.append("   • Datenqualität bei Data Gaps verbessern")
        
        report.append("")
        report.append("3. LANGFRISTIG (6-12 Monate):")
        report.append("   • Dynamische Pricing-Algorithmen implementieren")
        report.append("   • Personalisierte Preisgestaltung prüfen")
        report.append("   • Kontinuierliches Elastizitäts-Monitoring etablieren")
        
        report.append("")
        report.append("=" * 100)
        report.append("📚 METHODOLOGIE & QUELLEN")
        report.append("=" * 100)
        report.append("Portfolio-Segmentierung basiert auf:")
        report.append("  • Preiselastizität (Paczkowski, 2018)")
        report.append("  • Volumen-Quartile (BCG-Matrix-Ansatz)")
        report.append("  • Pricing-Strategien (Nagle et al., 2016)")
        report.append("  • Service-orientierte Architektur (Percival & Gregory, 2020)")
        report.append("=" * 100)
        
        return "\n".join(report)

    def export_segments_json(
        self,
        segments: Dict[str, List[Dict[str, Any]]],
        filename: str,
    ) -> None:
        """
        Export segments to JSON file for frontend consumption.
        
        Args:
            segments: Product segments
            filename: Output filename
        """
        # Calculate KPIs for each segment
        export_data = {
            "segments": {},
            "metadata": {
                "total_products": sum(len(products) for products in segments.values()),
                "segment_count": len(segments),
            }
        }
        
        for segment_name, products in segments.items():
            kpis = self.calculate_segment_kpis(products)
            
            export_data["segments"][segment_name] = {
                "kpis": kpis,
                "products": products,
            }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze product portfolio and create strategic pricing segments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="Base API URL (default: http://localhost:8000)"
    )
    
    parser.add_argument(
        "--country",
        type=str,
        help="Filter by country"
    )
    
    parser.add_argument(
        "--min-rsquared",
        type=float,
        default=0.4,
        help="Minimum R² for reliable data (default: 0.4)"
    )
    
    parser.add_argument(
        "--export",
        type=str,
        help="Export segments to JSON file"
    )
    
    args = parser.parse_args()
    
    analyzer = PortfolioAnalyzer(api_url=args.url)
    
    print("🔍 Lade Portfolio-Daten...")
    
    try:
        data = analyzer.fetch_all_elasticities(country=args.country)
    except httpx.HTTPError as e:
        print(f"❌ API-Fehler: {e}", file=sys.stderr)
        sys.exit(1)
    
    results = data.get("results", [])
    
    if not results:
        print("❌ Keine Elastizitätsdaten verfügbar", file=sys.stderr)
        sys.exit(1)
    
    print(f"✅ {len(results)} Produkte geladen")
    print("📊 Erstelle strategische Segmente...")
    
    segments = analyzer.create_strategic_segments(results, min_rsquared=args.min_rsquared)
    
    # Generate and print report
    report = analyzer.generate_portfolio_report(segments)
    print(report)
    
    # Export if requested
    if args.export:
        analyzer.export_segments_json(segments, args.export)
        print(f"\n💾 Segmente exportiert nach: {args.export}")
        print("   → Kann direkt im Frontend (AG Grid Dashboard) verwendet werden")


if __name__ == "__main__":
    main()
