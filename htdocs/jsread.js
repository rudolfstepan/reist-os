// Aufruf: js --read /htdocs/hello.js /htdocs/jsread.js
// Nur das explizit delegierte Objekt ist lesbar, kein Pfadzugriff aus JS.
if (!reist.files || reist.files.length !== 1) {
    console.error('Aufruf: js --read /htdocs/hello.js /htdocs/jsread.js');
    throw Error('Genau eine Lesefreigabe erforderlich');
}
const file = reist.files[0];
try {
    const size = file.size();
    const prefix = file.readText(64);
    file.seek(0);
    const bytes = new Uint8Array(file.read(64));
    if (size < 64 || !prefix.startsWith('// JS2 example') ||
        bytes.length !== 64 || bytes[0] !== 47) {
        throw Error('Bitte die mitgelieferte hello.js freigeben');
    }
    file.seek(size);
    if (file.read(1).byteLength !== 0) throw Error('EOF nicht erkannt');
    console.log('Dateigroesse:', size, 'Bytes; Vorschau:', prefix);
} finally {
    // OS-Ressourcen explizit freigeben, nicht auf Garbage Collection warten.
    file.close();
}
file.close(); // Idempotent: erneutes Close ist erlaubt.
let denied = false;
try { file.read(1); } catch (error) { denied = true; }
if (!denied) throw Error('Geschlossenes Objekt blieb lesbar');
print('JS_EXAMPLE_READ_OK');
