# 🦷 Zahnarztpraxis Urlaubs- & Raumplanung 2027 (Streamlit App)

Eine maßgeschneiderte, kostenfreie Web-Anwendung für die Urlaubs-, Überstunden- und Zimmerbelegungs-Planung einer Zahnarztpraxis mit **2 Zahnärzten, 4 Behandlungszimmern (2x Behandlung, 2x Prophylaxe)** und ~10 Mitarbeitern.

---

## 🌟 Hauptfunktionen
1. **Smarte Raum- & Kapazitätsanalyse:**
   - Berechnet automatisch für jeden Tag, wie viele der 4 Behandlungszimmer geöffnet sein können.
   - **Behandlung (Zimmer 1 & 2):** Prüft Kombination aus anwesenden Zahnärzten + Assistenzkräften.
   - **Prophylaxe (Zimmer 3 & 4):** Prüft anwesende Prophylaxe-Fachkräfte.
   - **Rezeption:** Prüft Mindestbesetzung der Anmeldung.
2. **Tages-Inspector:**
   - Mit einem Klick sehen Sie für jeden Tag, wer im Dienst/Urlaub/Krank ist, und erhalten konkrete Empfehlungen, welche Behandlungszimmer blockiert werden müssen.
3. **Rollen- & Rechte-System:**
   - **Mitarbeiter:** Eigenen Urlaub/Abwesenheiten beantragen, Plus/Minusstunden sehen, Masterkalender zur Abstimmung einsehen.
   - **Praxisleitung/Admin:** Anträge genehmigen/ablehnen mit Notizen, Mitarbeiter verwalten, Arbeitszeiten anpassen.
4. **Feiertage & Schulferien Baden-Württemberg 2027:**
   - Bereits integriert für eine übersichtliche Jahresplanung.
5. **Flexible Abwesenheiten & Überstundenkonto:**
   - Unterstützung für Urlaub (ganztags/halbtags), Überstundenabbau (stundenweise), Krankheit, Berufsschule und Fortbildung.

---

## 🚀 Schnellanleitung zur Inbetriebnahme (Lokal oder Cloud)

### Option A: Lokal auf dem Praxis-PC ausführen

1. **Python installieren:** Falls noch nicht vorhanden, Python (Version 3.9+) herunterladen und installieren.
2. **Abhängigkeiten installieren:**
   ```bash
   pip install -r requirements.txt
   ```
3. **App starten:**
   ```bash
   streamlit run app.py
   ```
4. Die App öffnet sich automatisch im Browser unter `http://localhost:8501`.

---

### Option B: 100% Kostenfrei Online-Hosten (Streamlit Community Cloud)

1. Den Code in ein kostenfreies **GitHub Repository** hochladen.
2. Auf [share.streamlit.io](https://share.streamlit.io) anmelden.
3. Repository auswählen und auf **Deploy** klicken.
4. Fertig! Ihre Mitarbeiter können nun weltweit vom Smartphone oder PC über einen gesicherten Link auf den Urlaubsplaner zugreifen.
