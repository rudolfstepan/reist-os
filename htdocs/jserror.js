// Aufruf: js /htdocs/jserror.js
// Eine absichtliche JS-Ausnahme wird aufgefangen; kein nativer Crash-Test.
let caught = false, cleaned = false;
try {
    throw new Error('Geplanter Testfehler');
} catch (error) {
    caught = error instanceof Error && error.message === 'Geplanter Testfehler';
    console.log('Aufgefangen:', error.message);
} finally {
    cleaned = true;
}
if (!caught || !cleaned) throw Error('Fehlerbehandlung fehlgeschlagen');
console.log('finally ausgefuehrt; das Skript laeuft weiter.');
print('JS_EXAMPLE_ERROR_OK');
