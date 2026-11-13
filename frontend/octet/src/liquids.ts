// Densities of common liquids, for the reagent table (gridview.ts): a liquid with no density typed takes its density
// from here. Values in g/mL at room temperature, from "Properties of Common Organic Solvents" (S. Murov, adapted by the
// ACS Division of Organic Chemistry, https://organicchemistrydata.org/solvents/), which takes them from the CRC Handbook
// of Chemistry and Physics (87th edition) and Vogel's Practical Organic Chemistry (5th edition). Densities are facts;
// the list is Octet's own. That table's nitromethane (1.382, its refractive index) is left out.
// Each liquid: its standard InChI (a drawn structure is matched by it), the names it is written by (text is matched by
// them, or by an abbreviation of Octet's with its InChI), its density, and whether a new table takes it as a solvent
// over or under an arrow (water and the simple alcohols are, as in "NaBH4, MeOH"; acids, amines and glycol are often
// reagents, so they start as reactants).
export type Liquid = { inchi: string; names: string[]; density: number; solvent?: true };
export const LIQUIDS: Liquid[] = [
  { inchi: "InChI=1S/C2H4O2/c1-2(3)4/h1H3,(H,3,4)", names: ["AcOH", "HOAc", "acetic acid", "CH3COOH", "CH3CO2H"], density: 1.0446 },
  { inchi: "InChI=1S/C3H6O/c1-3(2)4/h1-2H3", names: ["acetone", "Me2CO"], density: 0.7845, solvent: true },
  { inchi: "InChI=1S/C2H3N/c1-2-3/h1H3", names: ["MeCN", "CH3CN", "ACN", "acetonitrile"], density: 0.7857, solvent: true },
  { inchi: "InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H", names: ["benzene", "C6H6", "PhH"], density: 0.8765, solvent: true },
  { inchi: "InChI=1S/C4H10O/c1-2-3-4-5/h5H,2-4H2,1H3", names: ["nBuOH", "n-BuOH", "1-butanol", "butanol"], density: 0.8095, solvent: true },
  { inchi: "InChI=1S/C4H10O/c1-3-4(2)5/h4-5H,3H2,1-2H3", names: ["2-butanol", "sBuOH", "s-BuOH", "sec-butanol"], density: 0.8063 },
  { inchi: "InChI=1S/C4H8O/c1-3-4(2)5/h3H2,1-2H3", names: ["MEK", "butanone", "2-butanone", "methyl ethyl ketone"], density: 0.7999, solvent: true },
  { inchi: "InChI=1S/C4H10O/c1-4(2,3)5/h5H,1-3H3", names: ["tBuOH", "t-BuOH", "tert-butanol", "t-butanol"], density: 0.7887, solvent: true },
  { inchi: "InChI=1S/CCl4/c2-1(3,4)5", names: ["CCl4", "carbon tetrachloride", "tetrachloromethane"], density: 1.594, solvent: true },
  { inchi: "InChI=1S/C6H5Cl/c7-6-4-2-1-3-5-6/h1-5H", names: ["PhCl", "chlorobenzene"], density: 1.1058, solvent: true },
  { inchi: "InChI=1S/CHCl3/c2-1(3)4/h1H", names: ["CHCl3", "chloroform"], density: 1.4788, solvent: true },
  { inchi: "InChI=1S/C6H12/c1-2-4-6-5-3-1/h1-6H2", names: ["cyclohexane", "C6H12"], density: 0.7739, solvent: true },
  { inchi: "InChI=1S/C2H4Cl2/c3-1-2-4/h1-2H2", names: ["DCE", "1,2-dichloroethane", "1,2-DCE"], density: 1.245, solvent: true },
  { inchi: "InChI=1S/C4H10O/c1-3-5-4-2/h3-4H2,1-2H3", names: ["Et2O", "ether", "diethyl ether"], density: 0.713, solvent: true },
  { inchi: "InChI=1S/C6H14O3/c1-7-3-5-9-6-4-8-2/h3-6H2,1-2H3", names: ["diglyme"], density: 0.943, solvent: true },
  { inchi: "InChI=1S/C4H10O2/c1-5-3-4-6-2/h3-4H2,1-2H3", names: ["DME", "glyme", "1,2-dimethoxyethane"], density: 0.8637, solvent: true },
  { inchi: "InChI=1S/C3H7NO/c1-4(2)3-5/h3H,1-2H3", names: ["DMF", "dimethylformamide", "N,N-dimethylformamide"], density: 0.9445, solvent: true },
  { inchi: "InChI=1S/C2H6OS/c1-4(2)3/h1-2H3", names: ["DMSO", "dimethyl sulfoxide"], density: 1.092, solvent: true },
  { inchi: "InChI=1S/C4H8O2/c1-2-6-4-3-5-1/h1-4H2", names: ["dioxane", "1,4-dioxane"], density: 1.033, solvent: true },
  { inchi: "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3", names: ["EtOH", "ethanol"], density: 0.789, solvent: true },
  { inchi: "InChI=1S/C4H8O2/c1-3-6-4(2)5/h3H2,1-2H3", names: ["EtOAc", "AcOEt", "ethyl acetate"], density: 0.895, solvent: true },
  { inchi: "InChI=1S/C2H6O2/c3-1-2-4/h3-4H,1-2H2", names: ["ethylene glycol"], density: 1.115 },
  { inchi: "InChI=1S/C7H16/c1-3-5-7-6-4-2/h3-7H2,1-2H3", names: ["heptane", "n-heptane", "heptanes"], density: 0.684, solvent: true },
  { inchi: "InChI=1S/C6H18N3OP/c1-7(2)11(10,8(3)4)9(5)6/h1-6H3", names: ["HMPA"], density: 1.03 },
  { inchi: "InChI=1S/C6H14/c1-3-5-6-4-2/h3-6H2,1-2H3", names: ["hexane", "n-hexane", "hexanes"], density: 0.659, solvent: true },
  { inchi: "InChI=1S/CH4O/c1-2/h2H,1H3", names: ["MeOH", "methanol", "CH3OH"], density: 0.791, solvent: true },
  { inchi: "InChI=1S/C5H12O/c1-5(2,3)6-4/h1-4H3", names: ["MTBE", "TBME", "tert-butyl methyl ether"], density: 0.741, solvent: true },
  { inchi: "InChI=1S/CH2Cl2/c2-1-3/h1H2", names: ["DCM", "CH2Cl2", "dichloromethane", "methylene chloride"], density: 1.326, solvent: true },
  { inchi: "InChI=1S/C5H9NO/c1-6-4-2-3-5(6)7/h2-4H2,1H3", names: ["NMP", "N-methyl-2-pyrrolidinone", "N-methylpyrrolidone"], density: 1.033, solvent: true },
  { inchi: "InChI=1S/C5H12/c1-3-5-4-2/h3-5H2,1-2H3", names: ["pentane", "n-pentane", "pentanes"], density: 0.626, solvent: true },
  { inchi: "InChI=1S/C3H8O/c1-2-3-4/h4H,2-3H2,1H3", names: ["nPrOH", "n-PrOH", "1-propanol", "propanol"], density: 0.803, solvent: true },
  { inchi: "InChI=1S/C3H8O/c1-3(2)4/h3-4H,1-2H3", names: ["iPrOH", "i-PrOH", "IPA", "2-propanol", "isopropanol"], density: 0.785, solvent: true },
  { inchi: "InChI=1S/C5H5N/c1-2-4-6-5-3-1/h1-5H", names: ["pyridine", "py"], density: 0.982 },
  { inchi: "InChI=1S/C4H8O/c1-2-4-5-3-1/h1-4H2", names: ["THF", "tetrahydrofuran"], density: 0.8833, solvent: true },
  { inchi: "InChI=1S/C7H8/c1-7-5-3-2-4-6-7/h2-6H,1H3", names: ["toluene", "PhMe", "PhCH3"], density: 0.867, solvent: true },
  { inchi: "InChI=1S/C6H15N/c1-4-7(5-2)6-3/h4-6H2,1-3H3", names: ["Et3N", "NEt3", "TEA", "triethylamine"], density: 0.728 },
  { inchi: "InChI=1S/H2O/h1H2", names: ["H2O", "water"], density: 0.998, solvent: true },
  { inchi: "InChI=1S/H2O/h1H2/i/hD2", names: ["D2O", "heavy water"], density: 1.107 },
  { inchi: "InChI=1S/C8H10/c1-7-5-3-4-6-8(7)2/h3-6H,1-2H3", names: ["o-xylene"], density: 0.897, solvent: true },
  { inchi: "InChI=1S/C8H10/c1-7-4-3-5-8(2)6-7/h3-6H,1-2H3", names: ["m-xylene"], density: 0.868, solvent: true },
  { inchi: "InChI=1S/C8H10/c1-7-3-5-8(2)6-4-7/h3-6H,1-2H3", names: ["p-xylene"], density: 0.861, solvent: true },
];
