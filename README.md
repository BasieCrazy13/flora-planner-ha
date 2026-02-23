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

## 🌱 Planten Beheren

Je kunt planten eenvoudig toevoegen via de configuratie-knop:

1.  Ga naar de integratie pagina.
2.  Klik op **Configureren** bij Flora Planner.
3.  Kies **Voeg een nieuwe plant toe**.
4.  Vul de naam in en vink **AI gebruiken** aan.
5.  De AI doet een voorstel voor water, voeding en snoeien. Pas dit aan indien nodig en sla op.

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

Wil je snel planten toevoegen vanaf je dashboard? Omdat we variabelen gebruiken (de tekstvelden), moeten we hiervoor een **Script** gebruiken in Home Assistant.

1.  **Maak eerst drie helpers aan:**
    *   Ga naar **Instellingen** -> **Apparaten & Diensten** -> **Helpers**.
    *   Maak een **Tekst** helper aan met naam `Nieuwe Plant Naam` (entity id: `input_text.nieuwe_plant_naam`).
    *   Maak een **Tekst** helper aan met naam `Flora Zone Naam` (entity id: `input_text.flora_zone_naam`).
    *   Maak een **Schakelaar** helper aan met naam `Gebruik AI voor Plant` (entity id: `input_boolean.gebruik_ai_voor_plant`).

2.  **Maak een Script aan:**
    *   Ga naar **Instellingen** -> **Automatiseringen & Scenes** -> **Scripts**.
    *   Klik op **Script toevoegen** -> **Nieuw script**.
    *   Klik op de 3 puntjes rechtsboven -> **Bewerken in YAML**.
    *   Plak onderstaande code en sla op als `Flora Plant Toevoegen`:

```yaml
alias: Flora Plant Toevoegen
sequence:
  - service: flora_planner.add_plant
    data:
      zone_name: "{{ states('input_text.flora_zone_naam') }}"
      plant_name: "{{ states('input_text.nieuwe_plant_naam') }}"
      use_ai: "{{ states('input_boolean.gebruik_ai_voor_plant') }}"
  - service: input_text.set_value
    target:
      entity_id: input_text.nieuwe_plant_naam
    data:
      value: ""
  - service: input_boolean.turn_off
    target:
      entity_id: input_boolean.gebruik_ai_voor_plant
mode: single
icon: mdi:flower-plus
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
      - entity: input_boolean.gebruik_ai_voor_plant
        name: Gebruik AI voor advies
  - type: button
    name: Plant Toevoegen
    icon: mdi:plus
    tap_action:
      action: call-service
      service: script.flora_plant_toevoegen
```