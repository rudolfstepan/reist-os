// Aufruf: js /htdocs/jssafe.js  (bewusst ohne --read)
// API-Selbsttest, kein Ersatz fuer den nativen Script-Sandbox-Nachweis.
for (const name of ['require', 'process', 'os', 'std', 'fetch', 'document', 'window']) {
    if (typeof globalThis[name] !== 'undefined') {
        throw Error('Unerwartete Host-API: ' + name);
    }
}
if (typeof reist.files !== 'undefined') {
    throw Error('Dieses Beispiel ohne Dateifreigabe starten');
}
console.log('Keine impliziten Datei-, Netzwerk-, Prozess- oder DOM-APIs.');
print('JS_EXAMPLE_SAFE_OK');
