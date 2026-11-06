// What's new: each release's notes, newest first, in ASD-STE100 Simplified Technical English (brand/CLAUDE.md). The
// app shows the notes for its own version once after an update (Editor.tsx, seenNotes) and from About Octet Draw.
// docs/release-notes/<version>.md is the same text for GitHub; releases.check.ts keeps the two the same.

export type Release = { version: string; date: string; intro: string; sections: { title: string; items: string[] }[]; thanks: string };

export const RELEASES: Release[] = [
  {
    version: "1.1.0",
    date: "4 November 2026",
    intro: "Thank you to everyone who reported a problem or sent an idea. Your feedback made this release.",
    sections: [
      {
        title: "New",
        items: [
          "Experiment page. Go to File > New For > Experiment. It has the experiment details, a reagent table and a procedure.",
          "The reagent table calculates the mass, moles, equivalents and yield from your reaction.",
          "In a procedure, type *italic* or **bold**. LaTeX such as \\textit{}, $^2$ and $_2$ also works.",
          "Home has an Experiments list. You can search it, sort it and export it as CSV.",
          "Catalytic cycles: choose Side arrow in the cycle tool and click a step. Then choose Reagent or Product.",
          "Catalytic cycles: one side arrow can bring a reagent in and take a product out. A step can be reversible.",
          "Catalytic cycles: drag the end of an arc to set the space before or after an intermediate.",
          "Drag a charge, radical or lone pair to move it round its atom.",
          "A lone pair on a carbon with two bonds makes a carbene. Click a radical again to make a triplet.",
          "To hide a chemical warning, right-click its red circle and choose Hide this warning.",
          "Settings > General: choose the colour of the cursor and of the selection.",
          "Settings > Document > Page edges: show the page with its guides (such as journal columns), the page only, or none.",
          "Export: type a resolution up to 2400 dpi, or a size in pixels. You can also set the page colour as the background and the JPEG quality.",
          "Pictures from Octet (PDF, PNG and EMF) keep the drawing. Paste or drop one back into Octet to edit it.",
          "You can set a key for the hollow wedge and the dative bond in Settings > Keyboard shortcuts.",
        ],
      },
      {
        title: "Drawing windows",
        items: [
          "Your first drawing opens in the first window. Each drawing after that opens in a new window.",
          "A menu command now changes only the window in front. Before, it also changed the other open windows.",
        ],
      },
      {
        title: "Fixes",
        items: [
          "Copy into Word copies only the selection (#13). Export also exports only the selection (#8).",
          "Atom labels show when you paste into Word on Windows (#16).",
          "Press W over a wedge, or H over a hashed wedge, to turn it round, as in ChemDraw (#10).",
          "Clean Up keeps cycloalkynes as regular rings (#11).",
          "Name to Structure draws large molecules such as Taxol and strychnine with no warnings (#9).",
          "Delete removes only what you select. Text that belongs to an arrow or a structure stays (#12).",
          "The cursor shows on all backgrounds (#14).",
          "Chairs have the same angles as in ChemDraw. Two joined chairs keep all their atoms (#3).",
          "On Linux, the menu bar shows in each new window (#4).",
          "The cyclopentadienyl ligand (J key) shows its front and back edges correctly, also after you move it (#6).",
          "Hashed wedges have the same spacing as in ChemDraw. They have no extra line where they meet another bond (#7).",
          "Colour by element now colours B and Si. Br and I have colours of their own.",
          "The bead of a polymer bracket shows in front of its bond.",
          "A stacked NH label has the same space between N and H as in ChemDraw.",
          "Save, recent drawings, recovery and undo are more reliable. Octet asks before it saves over a file that another app changed (#2).",
        ],
      },
    ],
    thanks:
      "Special thanks to Prof-Dr-Stefan-Schramm, thewizardblizzard, mthaynes, Ciolkon, TomsLabYT, michemistry, jogisv23-cloud, Ameyanagi, FlamingLasrSwrd and kevinweil, and to all who wrote to us by email and on Reddit. To tell us more, use Help > Report a Problem.",
  },
];

export const notesFor = (version: string) => RELEASES.find((r) => r.version === version);
