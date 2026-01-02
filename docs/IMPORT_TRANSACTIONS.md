# Transaction Import Script

Einfaches Python-Script zum Importieren von CSV-Transaktionsdaten in die ElastiCom API.

## Installation

```powershell
pip install -r import_requirements.txt
```

## Verwendung

### Basis-Verwendung

```powershell
python import_transactions.py data/data.csv
```

### Mit Optionen

```powershell
# Custom Batch-Größe
python import_transactions.py data/data.csv --batch-size 500

# Limitierte Anzahl importieren
python import_transactions.py data/data.csv --limit 1000

# Custom API URL
python import_transactions.py data/data.csv --url http://localhost:8000

# Längerer Timeout
python import_transactions.py data/data.csv --timeout 60

# Kombiniert
python import_transactions.py data/data.csv --batch-size 100 --limit 5000 --url http://localhost:8000
```

## Optionen

- `csv_file`: Pfad zur CSV-Datei (erforderlich)
- `--url`: Basis-API-URL (Standard: `http://localhost:8000`)
- `--batch-size`: Anzahl Transaktionen pro Batch-Request (Standard: `1000`)
- `--limit`: Maximale Anzahl zu importierender Zeilen (Standard: alle)
- `--timeout`: Request-Timeout in Sekunden (Standard: `30`)

## CSV-Format

Das Script erwartet folgende Spalten:

- `InvoiceNo`: Rechnungsnummer
- `StockCode`: Artikelnummer
- `Description`: Produktbeschreibung (optional)
- `Quantity`: Menge (Integer)
- `InvoiceDate`: Datum im Format "M/D/YYYY H:MM" oder "D/M/YYYY H:MM"
- `UnitPrice`: Stückpreis (Decimal)
- `CustomerID`: Kundennummer (optional)
- `Country`: Land (optional)

## Beispiel-Output

```
📂 Reading transactions from data/data.csv
✅ Loaded 541909 transaction(s)
📤 Sending 542 batch(es) to http://localhost:8000
   Batch 1/542: 1000 transactions... ✅ 1000 created
   Batch 2/542: 1000 transactions... ✅ 1000 created
   ...
   Batch 542/542: 909 transactions... ✅ 909 created

🎉 Import complete! Created 541909 transaction(s)
```

## Fehlerbehandlung

- Ungültige Zeilen werden übersprungen und eine Warnung wird ausgegeben
- Bei API-Fehlern wird das Script mit Fehlerdetails beendet
- HTTP-Fehler zeigen die API-Response für besseres Debugging
