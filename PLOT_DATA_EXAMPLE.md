# Structure des Fichiers de Visualisation

## 📊 Fichier `*_plot_data_*.yaml`

Structure organisée pour créer facilement des graphiques de glycémie et bolus :

```yaml
metadata:
  period_name: "Breakfast"
  generated_at: "2026-09-11T21:07:19.123456"
  total_days: 3
  date_range: "2026/09/08 to 2026/09/10"
  description: "Données de glycémie et bolus pour Breakfast - prêtes pour visualisation"

days_data:
  - date: "2026/09/10"
    day_offset: -1
    bolus_events:
      - time: "08:05:05"
        carb_input: 15.0
        insulin_delivered: 1.175
        ic_ratio: 11.0
        bg_input: 125
        food_estimate: 1.35
        correction_estimate: -0.175
    bg_summary:
      start_bg: 123
      finish_bg: 137
      min_bg: 123
      max_bg: 177
      avg_bg: 145.2
      under_80_count: 0
      over_200_count: 0
      readings_count: 36
      time_window: "08:09:03-11:04:03"
    correction_boluses: []
    basal_summary:
      avg_rate: 0.5
      total_estimated: 1.5
      rate_changes: 1
      temp_basal_events: 0
```

## 🩸 Fichier `*_bg_detailed_*.yaml`

Toutes les lectures individuelles de glycémie pour un tracé détaillé :

```yaml
metadata:
  period_name: "Breakfast"
  generated_at: "2026-09-11T21:07:19.234567"
  description: "Lectures détaillées de glycémie pour Breakfast - tous les points individuels"

days_bg_data:
  - date: "2026/09/10"
    day_offset: -1
    readings_count: 36
    bg_readings:
      - timestamp: "2026/09/10 08:09:03"
        time: "08:09:03"
        value: 123
        type: "sensor"
      - timestamp: "2026/09/10 08:14:03"
        time: "08:14:03" 
        value: 125
        type: "sensor"
      # ... tous les points individuels
```

## 🎯 Usage pour Visualisation

Ces fichiers YAML sont optimisés pour :

- **Python plotting** (matplotlib, plotly, seaborn)
- **R visualization** (ggplot2, plotly)
- **JavaScript charts** (D3.js, Chart.js)
- **Excel/Google Sheets** (import YAML)

### Exemple Python simple :

```python
import yaml
import matplotlib.pyplot as plt
from datetime import datetime

# Charger les données
with open('breakfast_plot_data_3days_20260911.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Pour chaque jour
for day in data['days_data']:
    # Tracer les bolus
    for bolus in day['bolus_events']:
        time = datetime.strptime(f"{day['date']} {bolus['time']}", "%Y/%m/%d %H:%M:%S")
        plt.scatter(time, bolus['carb_input'], color='blue', s=bolus['insulin_delivered']*50)

# Charger les données BG détaillées
with open('breakfast_bg_detailed_20260911.yaml', 'r') as f:
    bg_data = yaml.safe_load(f)

# Tracer la glycémie
for day in bg_data['days_bg_data']:
    times = [datetime.strptime(r['timestamp'], "%Y/%m/%d %H:%M:%S") for r in day['bg_readings']]
    values = [r['value'] for r in day['bg_readings']]
    plt.plot(times, values, label=day['date'])

plt.xlabel('Temps')
plt.ylabel('Glycémie (mg/dL) / Carbs (g)')
plt.title('Réponse Glycémique - Petit-déjeuner')
plt.legend()
plt.show()
```

## 🔍 Inspection Visuelle Humaine

Les fichiers YAML sont lisibles directement pour :
- **Vérifier les données** avant visualisation
- **Identifier les patterns** manuellement  
- **Comprendre la chronologie** des événements
- **Valider les calculs** de ratios I:C

Parfait pour l'analyse clinique manuelle des données diabetes !