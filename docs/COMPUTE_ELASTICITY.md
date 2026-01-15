### Schritt 1: Die Daten vorbereiten (Zutaten bereitstellen)

Ganz am Anfang passiert etwas Simples, aber Wichtiges:

```python
prices_arr = np.array(prices)
quantities_arr = np.array(quantities)

```

**Was passiert hier?**
Python-Listen (die `[...]` Dinger) sind langsam und können nicht gut rechnen. Du kannst nicht einfach `liste * 2` machen.
NumPy Arrays (`np.array`) sind "Super-Listen". Mit ihnen können wir später Rechenoperationen auf **alle** Elemente gleichzeitig anwenden, ohne eine Schleife schreiben zu müssen.

---

### Schritt 2: Aufräumen (Die "Maske")

```python
valid_mask = (prices_arr > 0) & (quantities_arr > 0)
prices_arr = prices_arr[valid_mask]
quantities_arr = quantities_arr[valid_mask]

```

**Was passiert hier?**
Wir wollen die Preiselastizität berechnen. Dafür nutzen wir gleich Logarithmen. Der Logarithmus von 0 oder negativen Zahlen ist aber mathematisch unmöglich (gibt einen Fehler).

1. `prices_arr > 0`: NumPy prüft *jedes* Element. Ist es größer 0?
2. Das Ergebnis ist eine **Maske** aus `True` und `False` (z.B. `[True, True, False, True]`).
3. `prices_arr[valid_mask]`: Wir legen diese Maske über unsere Daten. Nur wo `True` steht, kommen die Daten weiter. Der Rest wird rausgefiltert.

---

### Schritt 3: Die Logarithmus-Transformation (Der Mathe-Trick)

```python
log_prices = np.log(prices_arr)
log_quantities = np.log(quantities_arr)

```

**Warum machen wir das?**
Das ist der Kern der Elastizitätsberechnung.

* Normalerweise ist die Beziehung zwischen Preis und Menge eine Kurve. Lineare Regression (Geraden ziehen) funktioniert auf Kurven schlecht.
* Wenn wir den Logarithmus (`ln`) von Preis und Menge nehmen, wird aus der Kurve oft eine **Gerade**.
* Der geniale Nebeneffekt: Die Steigung dieser Geraden ist direkt unsere **Preiselastizität**.

---

### Schritt 4: Die Matrix für die Regression bauen

```python
n = len(log_prices)
X = np.column_stack([np.ones(n), log_prices])
y = log_quantities

```

**Was passiert hier?**
Wir wollen eine Formel lösen, die aussieht wie:



(Menge = Basiswert + Elastizität * Preis)

NumPy braucht die Daten in einem bestimmten Format (Matrizen):

* `y`: Das sind unsere Zielwerte (Log-Mengen).
* `X`: Das sind unsere Eingabewerte.
* Warum `np.column_stack` und `np.ones`?
* Damit die Mathematik funktioniert, braucht die Regression eine Spalte mit Einsen (für den Basiswert ) und eine Spalte mit unseren Preisen (für die Steigung ). `column_stack` klebt diese beiden Spalten nebeneinander.



---

### Schritt 5: Die Lösung finden (Der "Solver")

```python
coeffs = np.linalg.lstsq(X, y, rcond=None)[0]
elasticity = coeffs[1]

```

**Was passiert hier?**

* `lstsq` steht für "Least Squares" (Methode der kleinsten Quadrate).
* NumPy versucht, eine Linie durch deine Datenpunkte zu ziehen, sodass der Abstand aller Punkte zur Linie minimal ist.
* Das Ergebnis `coeffs` enthält zwei Zahlen:
1. `coeffs[0]`: Der Schnittpunkt mit der Y-Achse (interessiert uns hier weniger).
2. `coeffs[1]`: Die Steigung der Linie. **Das ist unsere Elastizität!**



---

### Schritt 6: Wie gut war die Schätzung? ()

```python
y_pred = X @ coeffs
ss_res = np.sum((y - y_pred) ** 2)
ss_tot = np.sum((y - np.mean(y)) ** 2)
r_squared = 1 - (ss_res / ss_tot)

```

**Was passiert hier?**
Wir wollen wissen, ob unsere Linie wirklich zu den Punkten passt oder ob die Punkte wild verstreut sind.

* `X @ coeffs`: Das `@` ist Matrix-Multiplikation. Wir berechnen, welche Mengen unsere ideale Linie vorhersagen würde.
* Dann vergleichen wir die **Vorhersage** (`y_pred`) mit der **Realität** (`y`).
* `r_squared` ist eine Schulnote zwischen 0 und 1:
* 1.0 = Die Linie trifft jeden Punkt perfekt.
* 0.0 = Es gibt absolut keinen Zusammenhang zwischen Preis und Menge.



---

### Schritt 7: Zurück in die Realität

```python
original_prices = np.exp(log_prices)

```

Da wir vorhin alles logarithmiert haben (`np.log`), sind die Zahlen für Menschen schwer lesbar. Um Durchschnittspreise für den Bericht zu berechnen, machen wir das mit `np.exp` (Exponentialfunktion) rückgängig. Das ist quasi die "Un-Log"-Taste.

---

### Zusammenfassung für Einsteiger

1. **NumPy Arrays** machen die Listen rechenstark.
2. **Filterung** wirft ungültige Nullen raus.
3. **Log-Log** macht aus einer komplizierten Kurve eine einfache Gerade.
4. **lstsq** zieht die "perfekte Linie" durch die Punktwolke.
5. Die **Steigung** dieser Linie ist genau die Zahl, die du suchst (Elastizität).