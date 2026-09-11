// js /htdocs/jscolors.js [fail] -- no OS grants or persistent color state.
if (scriptArgs[1] === 'fail') reist.printColor('invalid', 'REJECTED_COLOR_PREFIX');
const palette = ['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'];
let rejected = 0;
for (const name of [undefined, null, 1, {}, new String('red'), 'RED', 'red\0', 'invalid']) {
    try { reist.printColor(name, 'REJECTED_COLOR_PREFIX'); } catch (error) { ++rejected; }
}
if (rejected !== 8) throw Error('color admission failed');
print('JS_COLOR_BEGIN');
for (let i = 0; i < 16; ++i) {
    const name = (i < 8 ? '' : 'bright-') + palette[i % 8];
    reist.printColor(name, 'PALETTE', i, name);
}
reist.printColor('cyan', 'x'.repeat(130));
reist.printColor('magenta', 'MULTI_A\nMULTI_B');
reist.printColor('yellow', 'SANITIZE', '\x1b\x7f\u00fc');
// Last lines stay visible even on VGA: independent RGB/default pixel proof.
reist.printColor('red', 'RED xxxxxxxxxxxxxxxx');
reist.printColor('green', 'GREEN xxxxxxxxxxxxxxxx');
reist.errorColor('blue', 'BLUE_STDERR xxxxxxxxxxxxxxxx');
print('DEFAULT wwwwwwwwwwwwwwww');
print('JS_COLOR_OK rejected=8');
