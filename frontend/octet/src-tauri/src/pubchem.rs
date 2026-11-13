// Name to Structure's online step (decision 0015): when nothing offline reads a name or an InChIKey and Settings >
// Online search is on, the page asks PubChem's PUG REST service for the structure, after the user presses Return.
// Only the typed text goes, to a fixed address. The answer is read as hostile: at most 64 KB, and each line must be
// SMILES and nothing else. The page reads that SMILES with its usual limits.
// The Properties panel's CAS row asks the same service for the CAS number of a structure the dictionary does not
// have (decision 0008). Only the structure's InChIKey goes, and only a CAS number with a right check digit comes back.
// The Properties panel's Find hazards (decision 0008) asks it for a structure's GHS classification, by the
// structure's standard InChIKey.
use std::time::Duration;

use tauri::{AppHandle, Manager};

const BY_NAME: &str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/property/SMILES/TXT";
const BY_KEY: &str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchikey/";
const BY_CID: &str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/";
const MOST_TEXT: usize = 300;
const MOST_ANSWER: usize = 64 * 1024;
// A compound's GHS classification: about 115 KB for ethanol or benzene, whose many sources PubChem lists.
const MOST_HAZARDS: usize = 1024 * 1024;
const MOST_SMILES: usize = 4000;
pub const UNREACHED: &str = "Octet cannot reach PubChem.";
pub const SEVERAL: &str = "PubChem has more than one structure for this name. Type a more exact name.";

// A standard InChIKey: 14 letters, 10 letters and one, with hyphens.
pub fn is_inchikey(s: &str) -> bool {
    let b = s.as_bytes();
    b.len() == 27 && b[14] == b'-' && b[25] == b'-' && b.iter().enumerate().all(|(i, c)| i == 14 || i == 25 || c.is_ascii_uppercase())
}

// The structure in PubChem's answer: one SMILES a line, one line for each compound with the name. None for no line;
// refused when the lines are not SMILES, or when they give more than one structure.
pub fn structure_of(answer: &str) -> Result<Option<String>, String> {
    let mut found: Option<&str> = None;
    for line in answer.lines().map(str::trim).filter(|l| !l.is_empty()) {
        let smiles = line.len() <= MOST_SMILES && line.bytes().all(|c| c.is_ascii_alphanumeric() || b"@+-[]()=#$:/\\.%*".contains(&c));
        if !smiles {
            return Err(UNREACHED.into());
        }
        match found {
            Some(f) if f != line => return Err(SEVERAL.into()),
            _ => found = Some(line),
        }
    }
    Ok(found.map(String::from))
}

// The first CAS registry number in PubChem's synonyms for a compound, which is its main one: two to seven digits, two
// digits and a check digit, with hyphens, the check digit right. None when there is none.
pub fn cas_in(synonyms: &str) -> Option<String> {
    synonyms.lines().map(str::trim).find(|line| {
        let parts: Vec<&str> = line.split('-').collect();
        let digits: Vec<u32> = line.bytes().filter(u8::is_ascii_digit).map(|c| u32::from(c - b'0')).collect();
        let shape = parts.len() == 3 && (2..=7).contains(&parts[0].len()) && parts[1].len() == 2 && parts[2].len() == 1 && digits.len() + 2 == line.len();
        // The check digit: the other digits from the right, times 1, 2, 3 and so on, added, modulo 10.
        shape && digits[..digits.len() - 1].iter().rev().zip(1..).map(|(d, i)| d * i).sum::<u32>() % 10 == digits[digits.len() - 1]
    }).map(String::from)
}

// Runs only when the user presses Return (or ⇧⌘N) on text nothing offline reads.
#[tauri::command]
pub async fn pubchem_structure(app: AppHandle, text: String) -> Result<Option<String>, String> {
    if !*app.state::<crate::search::Online>().0.lock().unwrap() {
        return Err("Online search is off in Settings.".into());
    }
    lookup(text.trim(), &app.package_info().version.to_string()).await
}

// Runs for the Properties panel, once for each structure the dictionary has no CAS number for.
#[tauri::command]
pub async fn pubchem_cas(app: AppHandle, key: String) -> Result<Option<String>, String> {
    if !*app.state::<crate::search::Online>().0.lock().unwrap() {
        return Err("Online search is off in Settings.".into());
    }
    cas_lookup(&key, &app.package_info().version.to_string()).await
}

// The client that asks PubChem. version: Octet's, for the user agent.
fn client(version: &str) -> Result<reqwest::Client, String> {
    // The updater installs the same provider; whichever runs first does it.
    if rustls::crypto::CryptoProvider::get_default().is_none() {
        let _ = rustls::crypto::ring::default_provider().install_default();
    }
    reqwest::Client::builder()
        .user_agent(format!("Octet Draw {version}"))
        .connect_timeout(Duration::from_secs(5))
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|_| UNREACHED.to_string())
}

// PubChem's answer as text, refused when larger than most bytes or not UTF-8. None when PubChem has nothing (404).
async fn answer(request: reqwest::RequestBuilder, most: usize) -> Result<Option<String>, String> {
    let mut response = request.send().await.map_err(|_| UNREACHED.to_string())?;
    if response.status() == reqwest::StatusCode::NOT_FOUND {
        return Ok(None);
    }
    if !response.status().is_success() {
        return Err(UNREACHED.into());
    }
    let mut body = Vec::new();
    while let Some(chunk) = response.chunk().await.map_err(|_| UNREACHED.to_string())? {
        body.extend_from_slice(&chunk);
        if body.len() > most {
            return Err(UNREACHED.into());
        }
    }
    String::from_utf8(body).map(Some).map_err(|_| UNREACHED.to_string())
}

// PubChem's structure for a name or InChIKey.
async fn lookup(text: &str, version: &str) -> Result<Option<String>, String> {
    if text.is_empty() || text.len() > MOST_TEXT || text.chars().any(char::is_control) {
        return Ok(None);
    }
    let client = client(version)?;
    // A name goes in the body, so no character of it can change the address.
    let request = if is_inchikey(text) {
        client.get(format!("{BY_KEY}{text}/property/SMILES/TXT"))
    } else {
        client.post(BY_NAME).header("Content-Type", "application/x-www-form-urlencoded").body(format!("name={}", crate::search::encode(text)))
    };
    match answer(request, MOST_ANSWER).await? {
        Some(text) => structure_of(&text),
        None => Ok(None),
    }
}

// PubChem's CAS number for a compound by its InChIKey. Nothing else can go in the address.
async fn cas_lookup(key: &str, version: &str) -> Result<Option<String>, String> {
    if !is_inchikey(key) {
        return Ok(None);
    }
    Ok(answer(client(version)?.get(format!("{BY_KEY}{key}/synonyms/TXT")), MOST_ANSWER).await?.and_then(|text| cas_in(&text)))
}

// The CID in PubChem's answer: its first line, digits only.
pub fn cid_of(answer: &str) -> Option<&str> {
    answer.lines().next().map(str::trim).filter(|c| (1..=12).contains(&c.len()) && c.bytes().all(|b| b.is_ascii_digit()))
}

// Runs only when the user presses Find hazards in the Properties panel.
#[tauri::command]
pub async fn pubchem_hazards(app: AppHandle, key: String) -> Result<Option<String>, String> {
    if !*app.state::<crate::search::Online>().0.lock().unwrap() {
        return Err("Online search is off in Settings.".into());
    }
    hazards(&key, &app.package_info().version.to_string()).await
}

// The GHS classification PubChem has for a compound's standard InChIKey, as PubChem's JSON, which the page reads as
// hostile (src/ghs.ts). Only the InChIKey goes, to fixed addresses: first for the compound's CID, then for its GHS
// Classification section. None when PubChem has no compound with the key, or no classification for it.
async fn hazards(key: &str, version: &str) -> Result<Option<String>, String> {
    if !is_inchikey(key) {
        return Ok(None);
    }
    let client = client(version)?;
    let Some(cids) = answer(client.get(format!("{BY_KEY}{key}/cids/TXT")), MOST_ANSWER).await? else {
        return Ok(None);
    };
    let cid = cid_of(&cids).ok_or(UNREACHED)?;
    answer(client.get(format!("{BY_CID}{cid}/JSON?heading=GHS+Classification")), MOST_HAZARDS).await
}

// A compound's Safety and Hazards section on PubChem's site, for a CID (the Properties panel's PubChem CID).
pub fn safety_page(cid: &str) -> Option<String> {
    cid_of(cid).filter(|c| *c == cid).map(|c| format!("https://pubchem.ncbi.nlm.nih.gov/compound/{c}#section=Safety-and-Hazards"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn inchikeys() {
        assert!(is_inchikey("BSYNRYMUTXBXSQ-UHFFFAOYSA-N"));
        assert!(!is_inchikey("BSYNRYMUTXBXSQ-UHFFFAOYSA-n"));
        assert!(!is_inchikey("BSYNRYMUTXBXSQ/UHFFFAOYSA-N"));
        assert!(!is_inchikey("aspirin"));
    }

    #[test]
    fn answers_are_smiles_or_refused() {
        assert_eq!(structure_of("CC(=O)OC1=CC=CC=C1C(=O)O\n").unwrap().as_deref(), Some("CC(=O)OC1=CC=CC=C1C(=O)O"));
        assert_eq!(structure_of("C[C@@H](C(=O)O)N\nC[C@@H](C(=O)O)N\n").unwrap().as_deref(), Some("C[C@@H](C(=O)O)N"));
        assert_eq!(structure_of("").unwrap(), None);
        assert_eq!(structure_of("CCO\nCCCO\n").unwrap_err(), SEVERAL);
        assert_eq!(structure_of("<script>alert(1)</script>").unwrap_err(), UNREACHED);
        assert_eq!(structure_of(&"C".repeat(MOST_SMILES + 1)).unwrap_err(), UNREACHED);
    }

    #[test]
    fn cas_numbers_have_a_right_check_digit() {
        assert_eq!(cas_in("aspirin\n2-acetoxybenzoic acid\n50-78-2\n11126-35-5\n").as_deref(), Some("50-78-2"));
        assert_eq!(cas_in("200-064-1\n50-78-1\n7732-18-5\n").as_deref(), Some("7732-18-5"), "an EC number and a wrong check digit are passed over");
        assert_eq!(cas_in("1-11-1\n12345678-12-1\n50-78-2x\n5O-78-2\n-50-78-2\n").as_deref(), None);
        assert_eq!(cas_in("").as_deref(), None);
    }

    #[test]
    fn cids_and_pages() {
        assert_eq!(cid_of("702\n"), Some("702"));
        assert_eq!(cid_of("702\n1234\n"), Some("702"));
        assert_eq!(cid_of("<html>"), None);
        assert_eq!(cid_of(""), None);
        assert_eq!(cid_of("1234567890123"), None);
        assert_eq!(safety_page("702").as_deref(), Some("https://pubchem.ncbi.nlm.nih.gov/compound/702#section=Safety-and-Hazards"));
        assert_eq!(safety_page("702\nevil"), None);
        assert_eq!(safety_page("702/../x"), None);
    }

    // Asks PubChem itself, so it runs only when asked: cargo test pubchem -- --ignored
    #[test]
    #[ignore]
    fn pubchem_answers() {
        let ask = |t: &str| tauri::async_runtime::block_on(lookup(t, "test"));
        assert_eq!(ask("aspirin").unwrap().as_deref(), Some("CC(=O)OC1=CC=CC=C1C(=O)O"));
        assert_eq!(ask("Tylenol / paracetamol & co").unwrap(), None);
        assert_eq!(ask("BSYNRYMUTXBXSQ-UHFFFAOYSA-N").unwrap().as_deref(), Some("CC(=O)OC1=CC=CC=C1C(=O)O"));
        assert_eq!(ask("qwertyuiopasdf").unwrap(), None);
        let cas = |k: &str| tauri::async_runtime::block_on(cas_lookup(k, "test"));
        assert_eq!(cas("BSYNRYMUTXBXSQ-UHFFFAOYSA-N").unwrap().as_deref(), Some("50-78-2"));
        assert_eq!(cas("aspirin").unwrap(), None);
        let hazards = |k: &str| tauri::async_runtime::block_on(hazards(k, "test"));
        assert!(hazards("LFQSCWFLJHTTHZ-UHFFFAOYSA-N").unwrap().unwrap().contains("GHS02"), "ethanol is flammable");
        assert_eq!(hazards("AAAAAAAAAAAAAA-UHFFFAOYSA-N").unwrap(), None);
    }
}
