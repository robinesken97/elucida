// Elucida: export a COPY of an MNova document (never the user's file) - each page as SVG, per NMR spectrum the
// nucleus, dimension, multiplet/peak counts and the multiplet/peak reports. Called by Elucida only as
//   MestReNova -nogui <this file> -sf "elucida_export,<copy>,<output folder>,<token>"
// manifest.json is written LAST (Elucida waits for it). Changes nothing in the document and saves nothing but the output.
function elucida_export(src, out, token) {
    function write(name, text) {
        var f = new File(out + "/" + name);
        if (f.open(File.WriteOnly)) {
            var s = new TextStream(f);
            s.codec = "UTF-8";
            s.write(text);
            f.close();
        }
    }
    function done(obj) {
        obj.token = token;
        write("manifest.json", JSON.stringify(obj));
    }
    // Windows (unchecked): a call might be handed to a running MNova with GUI - never touch that session, never exit it
    if (mainWindow.hasGui) {
        done({refused: "gui"});
        return;
    }
    var pages = [];
    try {
        if (!serialization.open(src)) {
            done({refused: "open"});
            return;
        }
        var dw = mainWindow.activeDocument;
        // only the document opened from the copy; its name is the path (the token is part of the file name)
        if (!dw || String(dw.name).indexOf(token) < 0) {
            done({refused: "doc"});
            return;
        }
        var n = dw.pageCount();
        for (var i = 0; i < n; i++) {
            var pg = dw.page(i);
            dw.setCurPage(pg);
            var spectra = [];
            var k = pg.itemCount("NMR Spectrum");
            for (var j = 0; j < k; j++) {
                var sp = new NMRSpectrum(pg.item(j, "NMR Spectrum"));
                var e = {nucleus: String(sp.nucleus()), dim: sp.dimCount, multiplets: 0, peaks: 0, mreport: "", preport: ""};
                try { e.multiplets = new Multiplets(sp.multiplets()).count; } catch (e1) { e.error = String(e1); }
                try { e.peaks = new Peaks(sp.peaks()).count; } catch (e2) { e.error = String(e2); }
                try {
                    var mr = MultipletReporter.getDefaultReporter();
                    mr.readSettings();
                    e.mreport = String(mr.report(sp, false) || "");
                } catch (e3) { e.error = String(e3); }
                try {
                    var pr = PeakReporter.getDefaultReporter();
                    pr.copySettings(PeakReporter.readSettings());
                    e.preport = String(pr.report(sp, false) || "");
                } catch (e4) { e.error = String(e4); }
                spectra.push(e);
            }
            var f = "page_" + (i + 1) + ".svg";
            serialization.save(out + "/" + f, "svg");     // returns false even on success: Elucida checks the file
            pages.push({page: i + 1, svg: f, spectra: spectra});
        }
    } catch (ex) {
        done({error: String(ex), pages: pages});
        Application.exit(0);
        return;
    }
    done({done: true, pages: pages});
    Application.exit(0);
}
