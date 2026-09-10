// Aufruf: js /htdocs/mandel.js
// Mandelbrot: z(n+1) = z(n)^2 + c, z(0) = 0, Flucht bei |z| > 2.
// Festes kleines Bild: keine Dateirechte, GUI, Timer oder Endlosschleife.
const width = 64, height = 24, maxIterations = 48;
const shades = ' .:-=+*#%@';
let inside = 0, outside = 0;
print('MANDELBROT_BEGIN width=64 height=24 iterations=48');
for (let y = 0; y < height; ++y) {
    const ci = (2 * y + 1 - height) * 0.05;
    let row = '|';
    for (let x = 0; x < width; ++x) {
        const cr = -2.2 + (x + 0.5) * 0.05;
        let zr = 0, zi = 0, iteration = 0;
        while (iteration < maxIterations && zr * zr + zi * zi <= 4) {
            const nextReal = zr * zr - zi * zi + cr;
            zi = 2 * zr * zi + ci;
            zr = nextReal;
            ++iteration;
        }
        if (iteration === maxIterations) {
            row += '@';
            ++inside;
        } else {
            row += shades[Math.min(shades.length - 2, Math.floor(iteration / 3))];
            ++outside;
        }
    }
    print(row + '|');
}
print('MANDELBROT_END');
if (!inside || !outside || inside + outside !== width * height) {
    throw Error('Mandelbrot-Selbsttest fehlgeschlagen');
}
print('JS_EXAMPLE_MANDEL_OK');
