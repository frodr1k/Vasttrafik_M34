# Västtrafik M34 (förbättrad)

Home Assistant-integration för avgångar via Västtrafik API v4 (Planera Resa).

## Nyheter i 2.0

- **State** visar nästa avgång: `kl. 07:18 (3 min) → Resecentrum`
- **Options**: filtrera på riktning (t.ex. `Resecentrum`) och linje
- Attribut `next_line`, `next_minutes_until`, `next_track`, …
- Delad `aiohttp`-session (HA-standard)
- Konfigurerbart intervall, tidsfönster och max per linje
- Dölj inställda avgångar (på som standard)
- Försening i state valfri (av som standard)
- Ikon utifrån trafikslag (buss/spårvagn/tåg)

## Installation

1. Kopiera mappen `custom_components/vasttrafik_m34` till din HA `config/custom_components/`
2. Starta om Home Assistant
3. **Inställningar → Enheter & tjänster → Lägg till → Västtrafik M34**
4. Klistra in **Authentication Key** från [developer.vasttrafik.se](https://developer.vasttrafik.se)
5. Sök hållplats (t.ex. `Näverstigen`) och välj rätt träff

## Options (efter setup)

Öppna integrationen → **Konfigurera**:

| Alternativ | Exempel |
|------------|---------|
| Riktning | `Resecentrum` |
| Linje | `Buss 6` |
| Visa försening | av/på |
| Tidsfönster | 90 min |
| Uppdatering | 60 s |

## Exempel state

```text
kl. 07:18 (3 min) → Resecentrum
```

## Exempel attribut

- `next_line`: Buss 6
- `next_destination`: Resecentrum via Stallsiken, …
- `next_departure_time`: 07:18
- `next_minutes_until`: 3
- `next_track`: B
- `departures_json`: lista med alla filtrerade avgångar

## TTS / template

```yaml
{{ state_attr('sensor.naverstigen_skovde', 'next_minutes_until') }}
```

eller bara `states('sensor.…')` för färdig text.
