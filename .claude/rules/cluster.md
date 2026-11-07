---
paths:
  - "elucida/app/cluster.py"
---

# Cluster: fachliche Regeln (nicht ändern ohne Rückfrage)

- Cluster (F6 Teil C, `app/cluster.py`, im Projektreiter Computerchemie: Statuskarte unter der Pfadliste, Ansicht rechts, keine Pop-ups; Ziel = Verbindung oder Reaktionspfad): nur Lesebefehle (`jobs_command`, `files_command`, `fetch_command`), nie Nicht an einen Cluster gebunden: jeder Linux-Server mit SSH-Schlüssel, Jobliste braucht Slurm (`squeue`, `sacct`), Ordnerliste GNU-`find`; Einrichtung im Handbuch „Cluster-Anbindung“, Link unter **Zugang**.
  Jobs starten oder abbrechen, keine frei eingebbaren Befehle; System-`ssh` mit Schlüssel/Agent, `BatchMode`, `StrictHostKeyChecking=yes`,
  kein Passwort in Elucida. Host/Benutzer/Ordner nur in QSettings `cluster/*`, nie im Projekt oder Repo. Dateinamen der Gegenseite
  sind nicht vertrauenswürdig (`parse_files`), Größe nach dem Holen prüfen. Abfrage alle `POLL_MS` (2 min, Windows 15 min: dort keine Sammelverbindung), solange die App offen ist (Nutzerwunsch), nur `squeue`; `sacct` nur beim Start, von Hand und wenn sich die Jobliste ändert. Fertige Jobs als Einblendung. Lehnt der Server den Login ab, stoppt die Abfrage bis „Aktualisieren“ (`login_refused`, Rechenzentren sperren sonst die IP).
