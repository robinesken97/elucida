<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/icon-dark.png">
    <img src="assets/icon.png" alt="Elucida" width="104">
  </picture>
</p>

<h1 align="center">Elucida</h1>

<p align="center">
  <b>From synthesis to Supporting Information.</b><br>
  Evaluate the analytical data of new compounds and get publication-ready figures and a complete SI in Word.
</p>

<p align="center">
  <a href="https://github.com/robinesken97/elucida/releases/latest"><img src="https://img.shields.io/github/v/release/robinesken97/elucida?label=release&color=2a7ae2" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/Windows%20·%20macOS%20·%20Linux-555" alt="Windows, macOS, Linux">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-555" alt="AGPL-3.0"></a>
</p>

<p align="center">
  <a href="#download">Download</a> &nbsp;·&nbsp;
  <a href="#workflows">Workflows</a> &nbsp;·&nbsp;
  <a href="docs/manual.en.md">Manual</a> &nbsp;·&nbsp;
  <a href="CHANGELOG.md">Changelog</a> &nbsp;·&nbsp;
  <a href="README.de.md">Deutsch</a>
</p>

<p align="center">
  <img src="docs/screenshots/welcome_dark_en.png" alt="Welcome page with a project and its compounds" width="900">
</p>

## What it does

- **One place per compound.** Spectra, structures and calculations live in a compound folder; a project groups the compounds of a paper and shows what is still missing.
- **Figures ready for the paper.** One consistent Origin-like style, PDF and SVG as vectors, 16 × 11 cm for half an A4 page.
- **The SI writes itself.** Characterisation paragraph, captions, data-processing text and crystal data go straight to Word, with templates for Wiley, ACS, RSC and Nature.
- **Raw data ready for a repository.** Data packages for TUDOdata and similar services, with lab codes and dates removed.
- **Draw right in the app.** The built-in editor (Octet Draw) handles structures, schemes and reagent tables; ChemDraw files keep working.

| Area | Tabs | Highlights |
|---|---|---|
| **Synthesis & analysis** | Synthesis · NMR · IR + EA · HRMS | Drawing editor, amount check, Mnova and TopSpin data, OPUS, Bruker `.d` |
| **UV-Vis & photophysics** | UV-Vis (ε) · Overlay · Fluorescence | Beer–Lambert fit with confidence interval, TD-DFT overlay, ORCA ESD |
| **Electrochemistry & EPR** | CV · SEC · EPR | E½, Nicholson, Randles–Ševčík, UV/Vis/NIR SEC, S = ½ fit, thermal decay |
| **Structure & computation** | X-Ray · DFT · Reaction paths | Mercury-style ORTEP, ORCA and Gaussian, orbitals, multireference, energy profiles |

## Workflows

**From compound to SI**

1. **New compound** on the welcome page, then **Compound …** for name and structure: draw it, or load a ChemDraw file.
2. Drag files into the window; Elucida sorts them into the right tab.
3. Adjust on the left, see the figure on the right. Labels, structures and insets can be dragged.
4. **SI (Word)** collects everything that is ready and lists what is missing.

**From project to paper**

Create a **project**, add compounds, and follow the checklist. **Complete SI** writes title page, contents and chapters; **Data packages** writes the dataset.

**Reaction paths across compounds**

Project → **Computational Chemistry**: copy calculations in, then compose profiles, molecules and orbital views on a free canvas. Diagrams are true to scale unless you explicitly choose a schematic layout, and they go into the complete SI.

**Spectroelectrochemistry without timestamps**

Merged UV/Vis/NIR exports contain no times. Elucida shows them by number and assigns potentials only after you confirm a schedule or a table, and it states that source in the SI.

Step-by-step guides with pictures: [synthesis to SI](docs/anleitungen/synthese-bis-si.en.md) · [UV-Vis ε](docs/anleitungen/uvvis-epsilon.en.md) · [CV and SEC](docs/anleitungen/elektrochemie.en.md) · [EPR](docs/anleitungen/epr.en.md) · [crystal structure and DFT](docs/anleitungen/struktur-dft.en.md)

No data at hand? **Help → Open example compound** fills all tabs with artificial data.

## Screenshots

<table>
  <tr>
    <td width="50%"><img src="docs/screenshots/paths_dark_en.png" alt="Reaction path canvas"><br><sub>Reaction paths</sub></td>
    <td width="50%"><img src="docs/screenshots/project_dark_en.png" alt="Project page"><br><sub>Project with checklists</sub></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/synthesis_dark_en.png" alt="Synthesis tab"><br><sub>Synthesis</sub></td>
    <td><img src="docs/screenshots/sec_dark_en.png" alt="SEC tab"><br><sub>Spectroelectrochemistry</sub></td>
  </tr>
</table>

## Download

Get the file for your system from the [latest release](https://github.com/robinesken97/elucida/releases/latest) and unzip it.

| System | File | Start |
|---|---|---|
| Windows | `Elucida-windows-x64.zip` | `Elucida\Elucida.exe` |
| macOS, Apple Silicon | `Elucida-macos-arm64.zip` | `Elucida.app` |
| macOS, Intel (macOS 14 or newer) | `Elucida-macos-x64.zip` | `Elucida.app` |
| Linux | `Elucida-linux-x64.AppImage` or `.tar.gz` | make executable, then start |

<details>
<summary><b>First launch: the app is not code-signed</b></summary>

- **Windows:** “More info” → “Run anyway”. Keep the whole `Elucida` folder together.
- **macOS:** move `Elucida.app` to Applications and open it once. Then System Settings → Privacy & Security → “Open Anyway”.
  Or in Terminal: `xattr -dr com.apple.quarantine /Applications/Elucida.app`
- **Linux:** `chmod +x Elucida-linux-x64.AppImage`. Needs `fuse3`; without it add `--appimage-extract-and-run`. Ubuntu 22.04 or newer.

</details>

Elucida checks once a day for a new version. To update, replace the app; compounds, projects and settings stay. It was called Spectravolt and UVVisTool before; old data is taken over automatically.

## Documentation

- [Manual](docs/manual.en.md): every tab and setting, supported data, troubleshooting, building from source
- [Changelog](CHANGELOG.md)

## License

[AGPL-3.0](LICENSE), without warranty. Bundled libraries and their licences are listed in the [manual](docs/manual.en.md#license). The drawing editor is based on [Octet Draw](https://github.com/SamChemMan/Octet-Draw) (Apache-2.0).
