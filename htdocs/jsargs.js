// Aufruf: js /htdocs/jsargs.js hallo 42
// Argumente bleiben Daten. print/log -> stdout, error -> stderr.
if (!Array.isArray(scriptArgs) || scriptArgs.length < 1 ||
    !scriptArgs.every(value => typeof value === 'string')) {
    throw Error('Ungueltige Argumentliste');
}
print('Hallo aus REIST JavaScript!');
console.log('Skript:', scriptArgs[0]);
console.log('Argumente:', scriptArgs.slice(1).join(' '));
console.error('Dies ist eine normale Testausgabe auf stderr.');
reist.setExitCode(0);
print('JS_EXAMPLE_ARGS_OK');
