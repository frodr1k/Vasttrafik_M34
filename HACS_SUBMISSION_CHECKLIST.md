# HACS Submission Checklist

## Automatiska Krav (ska passera utan fel)

### ✅ GitHub Actions
- [x] **HACS Action** - `.github/workflows/validate.yaml` skapad
  - Validerar: hacs.json, manifest.json, repository struktur
  - Körs: vid push, PR, dagligen kl 00:00, manuellt
  
- [x] **Hassfest** - `.github/workflows/validate.yaml` skapad  
  - Validerar: manifest.json enligt Home Assistant standards
  - Kontrollerar: dependencies, domain, version, etc.

- [x] **Test Workflow** - `.github/workflows/test.yml` finns
  - Kör unit tests på Python 3.11 och 3.12
  - Verifierar: syntax, struktur, Bronze Quality Scale

### ✅ Repository Innehåll
- [x] **hacs.json** finns och är giltig
  - name: "Västtrafik M34"
  - content_in_root: false
  - filename: "vasttrafik_m34"
  - render_readme: true
  - homeassistant: "2023.1.0"

- [x] **manifest.json** är giltig
  - domain: "vasttrafik_m34"
  - name: "Västtrafik M34"
  - version: "1.0.0"
  - documentation: https://github.com/frodr1k/Vasttrafik_M34
  - issue_tracker: https://github.com/frodr1k/Vasttrafik_M34/issues
  - quality_scale: "bronze"
  - integration_type: "service"

- [x] **README.md** finns
  - Komplett dokumentation på engelska och svenska
  - Installation instructions
  - Configuration guide
  - Usage examples
  - Troubleshooting

- [x] **LICENSE** finns (MIT)

### ⚠️ GitHub Release (MÅSTE GÖRAS)
- [ ] **Skapa en GitHub Release för v1.0.0**
  - Gå till: https://github.com/frodr1k/Vasttrafik_M34/releases/new
  - Tag: v1.0.0 (finns redan)
  - Release title: "v1.0.0 - Initial Production Release"
  - Description: Kopiera från nedan ⬇️

```markdown
# v1.0.0 - Initial Production Release 🎉

## 🥉 Bronze Quality Scale Certified

Perfect score: 20/20 Bronze Quality Scale rules met!

## ✨ Features

- **GUI-based configuration** - No YAML required
- **Smart auth-key reuse** - Enter once, use for multiple stations
- **Real-time departure monitoring** - Live updates from Västtrafik API v4
- **Station search** - Search and select any stop in Västtrafik's network
- **JSON formatted data** - `departures_json` attribute for easy parsing
- **Multiple departures** - Shows up to 15 departures per station
- **Delay tracking** - Real-time delay information
- **Cancellation detection** - Marks cancelled departures
- **Full bilingual support** - English and Swedish

## 📋 Requirements

- Home Assistant 2023.1.0 or newer
- Free Västtrafik API credentials from [developer.vasttrafik.se](https://developer.vasttrafik.se/)

## 🚀 Installation

Install via HACS or manually - see [README](https://github.com/frodr1k/Vasttrafik_M34/blob/master/README.md) for details.

## 🧪 Testing

- Comprehensive test suite
- CI/CD with GitHub Actions
- Python 3.11 and 3.12 support

## 📖 Documentation

Complete documentation available in the [README](https://github.com/frodr1k/Vasttrafik_M34/blob/master/README.md).

## 💚 Named After

The M34 tram - Gothenburg's newest and longest tram model! 🚊
```

---

## Repository Settings (Verifiera på GitHub)

### ⚠️ Settings att Kontrollera:
1. **Repository Description**
   - Gå till: https://github.com/frodr1k/Vasttrafik_M34/settings
   - Lägg till: "Home Assistant integration for Västtrafik public transport with GUI configuration - Named after the M34 tram! 🚊"

2. **Topics/Tags** 
   - Gå till: https://github.com/frodr1k/Vasttrafik_M34 (main page)
   - Klicka på kugghjulet bredvid "About"
   - Lägg till topics:
     - `home-assistant`
     - `home-assistant-component`
     - `home-assistant-custom`
     - `hacs`
     - `vasttrafik`
     - `public-transport`
     - `sweden`
     - `gothenburg`

3. **Issues**
   - Gå till: https://github.com/frodr1k/Vasttrafik_M34/settings
   - Under "Features", säkerställ att "Issues" är aktiverat ✅

4. **Country** (för hacs.json - valfritt men rekommenderat)
   - Eftersom detta är specifikt för Sverige, lägg till i `hacs.json`:
   ```json
   {
     "name": "Västtrafik M34",
     "country": ["SE"],
     "content_in_root": false,
     "filename": "vasttrafik_m34",
     "render_readme": true,
     "homeassistant": "2023.1.0"
   }
   ```

---

## Workflow för HACS Submission

### Steg 1: Vänta på att Actions ska köra klart
1. Gå till: https://github.com/frodr1k/Vasttrafik_M34/actions
2. Kontrollera att både "Validate" och "Test" workflows är gröna ✅
3. Om några fel: Fixa och pusha igen

### Steg 2: Skapa GitHub Release
1. Gå till: https://github.com/frodr1k/Vasttrafik_M34/releases/new
2. Välj tag: v1.0.0
3. Release title: "v1.0.0 - Initial Production Release"
4. Klistra in description från ovan
5. Klicka "Publish release"

### Steg 3: Verifiera Repository Settings
1. Description är satt
2. Topics är tillagda
3. Issues är aktiverade

### Steg 4: Lägg till i HACS Default Repository
1. Gå till: https://github.com/hacs/default
2. Klicka "Fork" (om du inte redan har en fork)
3. I din fork, gå till `integration` filen
4. Klicka "Edit this file"
5. Lägg till din integration **alfabetiskt**:
```json
{
  "name": "frodr1k/Vasttrafik_M34",
  "category": "integration"
}
```
6. Commit till en **ny branch** (inte master!)
7. Skapa Pull Request med denna template:

```markdown
## Repository

https://github.com/frodr1k/Vasttrafik_M34

## Summary

Home Assistant integration for monitoring Västtrafik public transport departures with real-time updates and GUI configuration.

## Category

- [x] Integration

## Checklist

- [x] I am the owner or a major contributor to this repository
- [x] The repository is public
- [x] The repository has issues enabled
- [x] The repository has a description
- [x] The repository has topics
- [x] HACS Action is added and passing
- [x] Hassfest is added and passing
- [x] A GitHub release has been created
- [x] Bronze Quality Scale certified (20/20 rules)

## Additional Information

This integration:
- Provides GUI-based configuration for Västtrafik's public transport API v4
- Supports station search across the entire Västtrafik network
- Shows real-time departure information with delays and cancellations
- Features smart auth-key reuse for multiple stations
- Includes comprehensive documentation in English and Swedish
- Has Bronze Quality Scale certification with full test coverage
- Named after the M34 tram - Gothenburg's newest and longest tram model 🚊

The integration is production-ready with v1.0.0 release and has been thoroughly tested.
```

### Steg 5: Vänta på Review
- HACS team kommer granska din PR
- Automatiska checks kommer köras
- Det kan ta några veckor/månader beroende på backlog
- Följ status här: https://github.com/hacs/default/pulls

---

## Efter Approval

När din PR är merged:
1. Vänta på nästa HACS scan (sker automatiskt)
2. Din integration kommer dyka upp i HACS som "default repository"
3. Användare kan installera direkt från HACS utan custom repository URL

---

## Snabbkommando Sammanfattning

```powershell
# 1. Uppdatera hacs.json med country
cd c:\git\Vasttrafik_M34

# 2. Commit och push
git add hacs.json
git commit -m "Add country code to hacs.json for HACS submission"
git push origin master

# 3. Vänta på Actions att bli gröna
# 4. Skapa GitHub Release på webben
# 5. Uppdatera repository description och topics på webben
# 6. Skapa HACS PR
```

---

## Länkar

- **HACS Documentation**: https://www.hacs.xyz/docs/publish/include/
- **HACS Default Repo**: https://github.com/hacs/default
- **GitHub Actions**: https://github.com/frodr1k/Vasttrafik_M34/actions
- **Releases**: https://github.com/frodr1k/Vasttrafik_M34/releases
