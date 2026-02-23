# 🌱 Flora Planner AI

[!HACS Custom](https://github.com/hacs/integration)
[!Home Assistant](https://www.home-assistant.io/)
[!License](LICENSE)

**Flora Planner AI** is een slimme Home Assistant integratie die je helpt je tuin te beheren. Het combineert lokale weersgegevens, bodemsensoren en **Google Gemini AI** om dynamische verzorgingsschema's en leuke wekelijkse verhalen te genereren.

Geen saaie schema's meer, maar een tuin die "leeft" en reageert op het weer!

## ✨ Functies

*   🤖 **AI-Powered:** Gebruikt Google Gemini om automatisch verzorgingsintervallen te schatten voor nieuwe planten.
*   🌦️ **Weer-bewust:**
    *   **Regen:** Als het meer dan 5mm heeft geregend, wordt de beurt overgeslagen en de teller gereset.
    *   **Hitte:** Bij temperaturen boven de 28°C wordt het interval automatisch verkort.
*   💧 **Bodemsensor Support:** Koppel optioneel een sensor; als de grond te droog is (<20%), krijg je direct een melding, ongeacht het schema.
*   📖 **Wekelijkse Verhalen:** Elke week genereert de AI een kort, leuk verhaaltje over de taken in jouw tuin.
*   🏡 **Multi-Zone:** Beheer aparte zones (bijv. "Achtertuin", "Balkon", "Kas").

## ⚙️ Hoe werkt het?

De integratie berekent elke dag of een plant water nodig heeft op basis van drie factoren:

1.  **Basis Interval:** Het standaard aantal dagen tussen waterbeurten.
2.  **Weersinvloeden:**
    *   *Heeft het geregend?* -> Reset de teller, vandaag geen water.
    *   *Is het heet?* -> Interval wordt tijdelijk korter (vaker water geven).
3.  **Noodsituaties:**
    *   *Bodemsensor droog?* -> Direct water geven!

## 📸 Screenshots

*(Voeg hier later screenshots toe van je sensor en configuratie flow)*

## 📥 Installatie

### Optie 1: Via HACS (Aanbevolen)
1.  Open HACS in Home Assistant.
2.  Ga naar **Integrations** > menu rechtsboven > **Custom repositories**.
3.  Voeg de URL van deze GitHub repository toe.
4.  Categorie: **Integration**.
5.  Zoek naar "Flora Planner AI" en klik op **Download**.
6.  Herstart Home Assistant.

### Optie 2: Handmatig
1.  Download de map `flora_planner` uit deze repository.
2.  Kopieer de map naar `config/custom_components/` op je Home Assistant server.
3.  Herstart Home Assistant.

## 🔧 Configuratie

1.  Ga naar **Instellingen** -> **Apparaten & Diensten**.
2.  Klik rechtsonder op **Integratie toevoegen**.
3.  Zoek naar **Flora Planner AI**.
4.  **Stap 1:** Voer je Google Gemini API Key in (deze is gratis voor persoonlijk gebruik).
5.  **Stap 2:** Geef je zone een naam (bijv. "Achtertuin") en selecteer je lokale weer-entiteit (bijv. `weather.forecast_home`).

## 🌱 Planten Beheren (De makkelijke manier)

De standaard manier om planten te beheren is via het menu. **Hier heb je geen helpers of codes voor nodig!**

1.  Ga naar **Instellingen** -> **Apparaten & Diensten**.
2.  Klik op **Configureren** bij de **Flora Planner** integratie.
3.  Kies **Voeg een nieuwe plant toe** of **Verwijder een plant**.
4.  Volg de stappen op het scherm (AI doet automatisch een voorstel).

## 📊 Sensoren

De integratie maakt één hoofdsensor aan per zone:
*   `sensor.flora_planner_[zone_naam]_weekly_story`

De status van deze sensor geeft aan of er een verhaal beschikbaar is. Het volledige verhaal en de status van de planten vind je in de **attributen** van deze sensor. Je kunt deze eenvoudig uitlezen in een Markdown kaart op je dashboard:

```yaml
type: markdown
content: >
  ## 🌻 Tuin Update
  {{ state_attr('sensor.flora_planner_achtertuin_weekly_story', 'full_story') }}

  ### 💧 Water nodig?
  {% set status = state_attr('sensor.flora_planner_achtertuin_weekly_story', 'plant_watering_status') %}
  {% for plant, nodig in status.items() %}
  - **{{ plant }}:** {{ 'Ja 🚰' if nodig else 'Nee ✅' }}
  {% endfor %}
```

## 🎨 Dashboard Kaart voor Planten Toevoegen

Wil je snel planten toevoegen vanaf je dashboard?

1.  **Maak eerst de helpers aan:**
    *   Ga naar **Instellingen** -> **Apparaten & Diensten** -> **Helpers**.
    *   Maak een **Tekst** helper aan met naam `Nieuwe Plant Naam` (entity id: `input_text.nieuwe_plant_naam`).
    *   Maak een **Tekst** helper aan met naam `Flora Zone Naam` (entity id: `input_text.flora_zone_naam`).
    *   Maak een **Schakelaar** helper aan met naam `Gebruik AI voor Plant` (entity id: `input_boolean.gebruik_ai_voor_plant`).
    *   *(Optioneel voor handmatig)* Maak een **Nummer** helper aan: `Water Interval` (entity id: `input_number.water_interval`, min 1, max 60).
    *   *(Optioneel voor handmatig)* Maak een **Nummer** helper aan: `Min Vochtigheid` (entity id: `input_number.min_vochtigheid`, min 0, max 100).
    *   *(Optioneel voor handmatig)* Maak een **Nummer** helper aan: `Zaaimaand` (entity id: `input_number.zaaimaand`, min 0, max 12).
    *   *(Optioneel voor handmatig)* Maak een **Nummer** helper aan: `Oogstmaand` (entity id: `input_number.oogstmaand`, min 0, max 12).

2.  **Maak de Scripts aan:**
    *   Ga naar **Instellingen** -> **Automatiseringen & Scenes** -> **Scripts**.
    
    **Script 1: Flora AI Advies (Sla op als `flora_ai_advies`)**
```yaml
alias: Flora AI Advies
sequence:
  - service: flora_planner.get_ai_advice
    data:
      plant_name: "{{ states('input_text.nieuwe_plant_naam') }}"
      zone_name: "{{ states('input_text.flora_zone_naam') }}"
    response_variable: ai_advies
  - service: input_number.set_value
    target:
      entity_id: input_number.water_interval
    data:
      value: "{{ ai_advies.watering_interval | int(default=7) }}"
  - service: input_number.set_value
    target:
      entity_id: input_number.min_vochtigheid
    data:
      value: "{{ ai_advies.min_moisture | int(default=20) }}"
  - service: input_number.set_value
    target:
      entity_id: input_number.zaaimaand
    data:
      value: "{{ ai_advies.sowing_month | int(default=0) }}"
  - service: input_number.set_value
    target:
      entity_id: input_number.oogstmaand
    data:
      value: "{{ ai_advies.harvesting_month | int(default=0) }}"
  - service: persistent_notification.create
    data:
      title: "Advies voor {{ states('input_text.nieuwe_plant_naam') }}"
      message: "{{ ai_advies.advice }}"
mode: single
icon: mdi:robot
```

    **Script 2: Flora Plant Toevoegen (Sla op als `flora_plant_toevoegen`)**
```yaml
alias: Flora Plant Toevoegen
sequence:
  - service: flora_planner.add_plant
    data:
      zone_name: "{{ states('input_text.flora_zone_naam') }}"
      plant_name: "{{ states('input_text.nieuwe_plant_naam') }}"
      use_ai: false  # We hebben het advies al opgehaald, dus nu niet meer overschrijven!
      watering_interval: "{{ states('input_number.water_interval') | int(default=7) }}"
      sowing_month: "{{ states('input_number.zaaimaand') | int(default=0) }}"
      harvesting_month: "{{ states('input_number.oogstmaand') | int(default=0) }}"
      min_moisture: "{{ states('input_number.min_vochtigheid') | int(default=20) }}"
  - service: input_text.set_value
    target:
      entity_id: input_text.nieuwe_plant_naam
    data:
      value: ""
mode: single
icon: mdi:flower
```

3.  **Gebruik deze YAML code voor je dashboard kaart:**

```yaml
type: vertical-stack
cards:
  - type: entities
    entities:
      - entity: input_text.flora_zone_naam
        name: Zone (bijv. Achtertuin)
      - entity: input_text.nieuwe_plant_naam
        name: Naam van de plant
  - type: horizontal-stack
    cards:
      - type: button
        name: Vraag AI Advies
        icon: mdi:robot
        tap_action:
          action: call-service
          service: script.flora_ai_advies
      - type: button
        name: Plant Toevoegen
        icon: mdi:plus
        tap_action:
          action: call-service
          service: script.flora_plant_toevoegen
  - type: entities
    entities:
      - entity: input_number.water_interval
        name: Water Interval (dagen)
      - entity: input_number.min_vochtigheid
        name: Min. Vochtigheid (%)
      - entity: input_number.zaaimaand
        name: Zaaimaand (0=nvt)
      - entity: input_number.oogstmaand
        name: Oogstmaand (0=nvt)
```