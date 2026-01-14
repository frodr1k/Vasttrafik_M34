# Västtrafik M34 - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/github/v/release/frodr1k/Vasttrafik_M34)](https://github.com/frodr1k/Vasttrafik_M34/releases)
[![Test](https://github.com/frodr1k/Vasttrafik_M34/actions/workflows/test.yml/badge.svg)](https://github.com/frodr1k/Vasttrafik_M34/actions/workflows/test.yml)
[![Quality](https://img.shields.io/badge/Quality-Bronze%20100%25-cd7f32)](https://developers.home-assistant.io/docs/integration_quality_scale_index/)

A Home Assistant custom integration for monitoring Västtrafik public transport departures with real-time updates and GUI configuration.

Named after the M34 tram, the newest and longest tram model in Gothenburg's fleet! 🚊

**🥉 Bronze Quality Standard** - This integration meets Home Assistant's Bronze quality requirements with comprehensive test coverage.

_🇸🇪 [Swedish version below](#västtrafik-m34---svensk-version) / Svenska beskrivning nedan_

---

## ✨ Features

- ✅ **GUI-based configuration** - No YAML required
- ✅ **Smart auth-key reuse** - Enter auth-key only once for multiple stations
- ✅ **Station search** - Search and select any stop in Västtrafik's network
- ✅ **Real-time departures** - Live updates with delay information
- ✅ **JSON departures data** - Structured `departures_json` attribute for easy parsing
- ✅ **Multiple departures** - Shows up to 15 departures per station
- ✅ **Delay tracking** - Shows delays in minutes
- ✅ **Cancellation detection** - Marks cancelled departures
- ✅ **Track/platform info** - Shows departure track when available
- ✅ **Automatic token refresh** - OAuth2 tokens managed automatically
- ✅ **Bilingual** - Full English and Swedish support
- ✅ **Bronze Quality Standard** - Comprehensive test coverage and CI/CD

## 📋 Requirements

- Home Assistant 2023.1.0 or newer
- Västtrafik API credentials (free at https://developer.vasttrafik.se/)
- Subscribe to **"API Planera Resa"** v4 in the developer portal

## 🚀 Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the menu (⋮) in top right corner
4. Select "Custom repositories"
5. Add URL: `https://github.com/frodr1k/Vasttrafik_M34`
6. Select category: "Integration"
7. Click "Add"
8. Find "Västtrafik M34" and click "Download"
9. **Restart Home Assistant**

### Manual Installation

1. Copy the `custom_components/vasttrafik_m34` folder to your `config/custom_components` directory
2. Restart Home Assistant

## ⚙️ Configuration

### Step 1: Get API Credentials

1. Go to https://developer.vasttrafik.se/
2. Create an account (free)
3. Log in and create a new application
4. Subscribe to **"API Planera Resa"** (Journey Planning API) - Select v4
5. Copy your **Authentication Key** (Autentiseringsnyckel)
   - This is a base64-encoded string that looks like:
   ```
   bXlDbGllbnRJZDpteUNsaWVudFNlY3JldA==
   ```
   - It's the combined `client_id:client_secret` in base64 format
   - **⚠️ IMPORTANT**: This is YOUR secret key - never share it publicly!

### Step 2: Add Integration in Home Assistant

1. Go to **Settings** → **Devices & Services**
2. Click **"+ ADD INTEGRATION"**
3. Search for **"Västtrafik M34"**
4. Follow the configuration wizard:
   - **Enter Authentication Key**: Paste your Authentication Key from the portal
     - ℹ️ **Note**: You only need to enter this once during initial setup
     - When adding additional stations, the integration will automatically reuse the existing authentication key
     - You'll only be asked for it again if the token has expired or been invalidated
   - **Search for Station**: Type at least 2 characters (e.g., "Central", "Brunns")
   - **Select Station**: Pick your station from the results
5. Done! The integration will create a sensor entity

## 📊 Usage

The integration creates a sensor showing minutes until next departure with rich attributes.

### Sensor State

The sensor state shows time until next departure:
- **"Nu"** - Departing now
- **"1 min"** - Departing in 1 minute  
- **"5 min"** - Departing in 5 minutes
- **"Inga avgångar"** - No departures available

### Sensor Attributes

```yaml
sensor.vasttrafik_centralstationen:
  state: "2 min"
  attributes:
    station_name: "Centralstationen"
    station_gid: "9021014001760000"
    departure_count: 8
    departures:
      - "16 → Bergsjön - 2 min 🔴"
      - "16 → Bergsjön - 12 min"
      - "19 → Ånäsvägen - 5 min (+2 min) 🔴"
      - "19 → Ånäsvägen - 15 min"
      - "6 → Chalmers - 7 min 🔴"
    last_update: "2026-01-13T15:30:00"
```

**Indicators:**
- **🔴** = Real-time data available (estimated time)
- **(+X min)** = Delayed by X minutes
- **(-X min)** = Earlier than scheduled
- **[INSTÄLLD]** = Cancelled departure

### Example Automations

#### Notify When Tram Departing Soon

```yaml
automation:
  - alias: "Tram leaving soon"
    trigger:
      - platform: state
        entity_id: sensor.vasttrafik_centralstationen
    condition:
      - condition: template
        value_template: >
          {% set state = states('sensor.vasttrafik_centralstationen') %}
          {{ state not in ['unknown', 'unavailable', 'Inga avgångar'] 
             and state.endswith(' min') 
             and state.split()[0]|int <= 3 }}
    action:
      - service: notify.mobile_app
        data:
          title: "Spårvagn går snart!"
          message: "Nästa spårvagn från Centralstationen går om {{ states('sensor.vasttrafik_centralstationen') }}"
```

#### Show Next 3 Departures in Lovelace

```yaml
type: entities
entities:
  - entity: sensor.vasttrafik_centralstationen
title: Centralstationen
state_color: true
```

Or use a markdown card for detailed view:

```yaml
type: markdown
content: |
  ## 🚊 Centralstationen
  
  **Nästa avgång:** {{ states('sensor.vasttrafik_centralstationen') }}
  
  {% for departure in state_attr('sensor.vasttrafik_centralstationen', 'departures')[:5] %}
  - {{ departure }}
  {% endfor %}
  
  _Uppdaterad: {{ state_attr('sensor.vasttrafik_centralstationen', 'last_update') | as_timestamp | timestamp_custom('%H:%M') }}_
```

## 🔧 Technical Details

### OAuth2 Authentication

- Uses OAuth2 Client Credentials flow
- Tokens valid for 24 hours (86400 seconds)
- Automatic refresh 5 minutes before expiry
- Secure token storage in config entry

### API Endpoints (v4)

1. **Token**: `POST https://ext-api.vasttrafik.se/token`
2. **Search**: `GET https://ext-api.vasttrafik.se/pr/v4/locations/by-text`
3. **Departures**: `GET https://ext-api.vasttrafik.se/pr/v4/stop-areas/{gid}/departures`

### Update Frequency

- Departures updated every **60 seconds**
- Minimal API calls (token cached, only departures fetched regularly)
- Network-efficient design

## 🐛 Troubleshooting

### Integration doesn't appear after HACS installation

- Restart Home Assistant after installing via HACS
- Check Home Assistant logs for errors
- Verify `custom_components/vasttrafik_m34` directory exists

### "Invalid authentication key" error

- Verify you copied the **full** Authentication Key from the portal
- Check that it's the base64-encoded key, not client_id or client_secret separately
- Ensure your application has subscribed to "API Planera Resa" v4

### "Cannot connect" error

- Check your internet connection
- Verify developer.vasttrafik.se is accessible
- Check Home Assistant logs for detailed error messages

### No departures showing

- Verify the station you selected has departures in the next hour
- Check if it's late at night (limited service)
- Try reconfiguring with a different station

### Station search returns no results

- Try searching with different terms
- Use Swedish station names (e.g., "Centralstationen" not "Central Station")
- Try partial names (e.g., "Brunns" for "Brunnsparken")

## 📖 Additional Information

### Why "M34"?

The M34 is Gothenburg's newest and longest tram model - a perfect symbol for modern public transport! 🚊

### API Documentation

- Västtrafik Developer Portal: https://developer.vasttrafik.se/
- API v4 Documentation: https://github.com/vasttrafik/api-pr-docs

### License

MIT License - See [LICENSE](LICENSE) file for details

### Issues & Contributions

- Report issues: https://github.com/frodr1k/Vasttrafik_M34/issues
- Contributions welcome via pull requests

---

# Västtrafik M34 - Svensk Version

En Home Assistant-integration för övervakning av Västtrafiks avgångar i realtid med GUI-konfiguration.

Döpt efter M34-spårvagnen, den nyaste och längsta spårvagnsmodellen i Göteborgs flottan! 🚊

## ✨ Funktioner

- ✅ **GUI-baserad konfiguration** - Ingen YAML krävs
- ✅ **Hållplatssökning** - Sök och välj valfri hållplats i Västtrafiks nät
- ✅ **Realtidsavgångar** - Live-uppdateringar med förseningsinformation
- ✅ **Förseningsspårning** - Visar förseningar i minuter
- ✅ **Inställningsdetektering** - Markerar inställda avgångar
- ✅ **Realtidsindikator** - Visuell indikator för realtidsdata
- ✅ **Automatisk tokenuppdatering** - OAuth2-tokens hanteras automatiskt
- ✅ **Tvåspråkig** - Fullt stöd för engelska och svenska

## 📋 Krav

- Home Assistant 2023.1.0 eller nyare
- Västtrafiks API-uppgifter (gratis på https://developer.vasttrafik.se/)
- Prenumerera på **"API Planera Resa"** v4 i utvecklarportalen

## 🚀 Installation

### Via HACS (Rekommenderas)

1. Öppna HACS i Home Assistant
2. Klicka på "Integrations"
3. Klicka på menyn (⋮) längst upp till höger
4. Välj "Custom repositories"
5. Lägg till URL: `https://github.com/frodr1k/Vasttrafik_M34`
6. Välj kategori: "Integration"
7. Klicka "Add"
8. Hitta "Västtrafik M34" och klicka "Download"
9. **Starta om Home Assistant**

### Manuell Installation

1. Kopiera mappen `custom_components/vasttrafik_m34` till din `config/custom_components`-katalog
2. Starta om Home Assistant

## ⚙️ Konfiguration

### Steg 1: Hämta API-Uppgifter

1. Gå till https://developer.vasttrafik.se/
2. Skapa ett konto (gratis)
3. Logga in och skapa en ny applikation
4. Prenumerera på **"API Planera Resa"** (Journey Planning API) - Välj v4
5. Kopiera din **Autentiseringsnyckel**
   - Detta är en base64-kodad sträng som ser ut så här:
   ```
   bXlDbGllbnRJZDpteUNsaWVudFNlY3JldA==
   ```
   - Det är den kombinerade `client_id:client_secret` i base64-format
   - **⚠️ VIKTIGT**: Detta är DIN hemliga nyckel - dela aldrig den offentligt!

### Steg 2: Lägg till Integration i Home Assistant

1. Gå till **Inställningar** → **Enheter & Tjänster**
2. Klicka **"+ LÄGG TILL INTEGRATION"**
3. Sök efter **"Västtrafik M34"**
4. Följ konfigurationsguiden:
   - **Ange Autentiseringsnyckel**: Klistra in din autentiseringsnyckel från portalen
     - ℹ️ **OBS**: Du behöver bara ange denna en gång vid första installationen
     - När du lägger till fler hållplatser återanvänder integrationen automatiskt den befintliga autentiseringsnyckeln
     - Du kommer bara bli tillfrågad igen om token har gått ut eller blivit ogiltig
   - **Sök Hållplats**: Skriv minst 2 tecken (t.ex. "Central", "Brunns")
   - **Välj Hållplats**: Välj din hållplats från resultaten
5. Klart! Integrationen skapar en sensor-entitet

## 📊 Användning

Integrationen skapar en sensor som visar minuter till nästa avgång med detaljerade attribut.

### Sensor-Tillstånd

Sensorns tillstånd visar tid till nästa avgång:
- **"Nu"** - Avgår nu
- **"1 min"** - Avgår om 1 minut  
- **"5 min"** - Avgår om 5 minuter
- **"Inga avgångar"** - Inga avgångar tillgängliga

### Sensor-Attribut

```yaml
sensor.vasttrafik_centralstationen:
  state: "2 min"
  attributes:
    station_name: "Centralstationen"
    station_gid: "9021014001760000"
    departure_count: 8
    departures:
      - "16 → Bergsjön - 2 min 🔴"
      - "16 → Bergsjön - 12 min"
      - "19 → Ånäsvägen - 5 min (+2 min) 🔴"
      - "19 → Ånäsvägen - 15 min"
      - "6 → Chalmers - 7 min 🔴"
    last_update: "2026-01-13T15:30:00"
```

**Indikatorer:**
- **🔴** = Realtidsdata tillgänglig (beräknad tid)
- **(+X min)** = Försenad X minuter
- **(-X min)** = Tidigare än planerat
- **[INSTÄLLD]** = Inställd avgång

## 🔧 Tekniska Detaljer

### OAuth2-Autentisering

- Använder OAuth2 Client Credentials-flöde
- Tokens giltiga i 24 timmar (86400 sekunder)
- Automatisk uppdatering 5 minuter före utgång
- Säker tokenlagring i konfigurationen

### API-Endpoints (v4)

1. **Token**: `POST https://ext-api.vasttrafik.se/token`
2. **Sökning**: `GET https://ext-api.vasttrafik.se/pr/v4/locations/by-text`
3. **Avgångar**: `GET https://ext-api.vasttrafik.se/pr/v4/stop-areas/{gid}/departures`

### Uppdateringsfrekvens

- Avgångar uppdateras varje **60 sekund**
- Minimala API-anrop (token cachas, endast avgångar hämtas regelbundet)
- Nätverkseffektiv design

## 🐛 Felsökning

### Integrationen syns inte efter HACS-installation

- Starta om Home Assistant efter installation via HACS
- Kontrollera Home Assistant-loggarna för fel
- Verifiera att katalogen `custom_components/vasttrafik_m34` finns

### Fel "Invalid authentication key"

- Verifiera att du kopierat **hela** Autentiseringsnyckeln från portalen
- Kontrollera att det är den base64-kodade nyckeln, inte client_id eller client_secret separat
- Säkerställ att din applikation har prenumererat på "API Planera Resa" v4

### Fel "Cannot connect"

- Kontrollera din internetanslutning
- Verifiera att developer.vasttrafik.se är tillgänglig
- Kolla Home Assistant-loggarna för detaljerade felmeddelanden

### Inga avgångar visas

- Verifiera att hållplatsen du valde har avgångar inom nästa timme
- Kontrollera om det är sent på natten (begränsad trafik)
- Prova att konfigurera om med en annan hållplats

### Hållplatssökning ger inga resultat

- Prova att söka med olika termer
- Använd svenska hållplatsnamn (t.ex. "Centralstationen" inte "Central Station")
- Prova delar av namnet (t.ex. "Brunns" för "Brunnsparken")

## �‍💻 Development & Testing

### Running Tests

This integration includes comprehensive automated tests.

#### Install test dependencies:
```bash
pip install -r requirements_test.txt
```

#### Run all tests:
```bash
pytest tests/ -v
```

#### Run with coverage:
```bash
pytest tests/ -v --cov=custom_components --cov-report=term-missing
```

### Test Coverage

- **23 automated tests** covering:
  - Config flow (9 tests)
  - Integration setup (6 tests)
  - Sensor platform (8 tests)
- **CI/CD:** GitHub Actions runs tests on every push
- **Python:** Tests run on Python 3.11 and 3.12

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/ -v`
5. Submit a pull request

All PRs must pass automated tests before merge!

## �📖 Ytterligare Information

### Varför "M34"?

M34 är Göteborgs nyaste och längsta spårvagnsmodell - en perfekt symbol för modern kollektivtrafik! 🚊

### Quality Standard

This integration achieves Home Assistant's **Bronze Quality Standard** with:
- ✅ Comprehensive test coverage
- ✅ Automated CI/CD pipeline
- ✅ Proper dependency management
- ✅ All Bronze requirements met (11/11)

### Licens

MIT-licens - Se [LICENSE](LICENSE)-filen för detaljer

### Problem & Bidrag

- Rapportera problem: https://github.com/frodr1k/Vasttrafik_M34/issues
- Bidrag välkomnas via pull requests
