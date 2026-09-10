// Aufruf: js /htdocs/jsmath.js
// Kleine, feste Schleifen: kein Benchmark und keine Endlosschleife.
function fibonacci(count) {
    let a = 0, b = 1;
    for (let i = 0; i < count; ++i) [a, b] = [b, a + b];
    return a;
}
const numbers = [1, 2, 3, 4, 5];
const squares = numbers.map(value => value * value);
const sum = squares.reduce((total, value) => total + value, 0);
const fib = fibonacci(20);
if (sum !== 55 || fib !== 6765 || Math.sqrt(81) !== 9) {
    throw Error('Rechenergebnis falsch');
}
console.log('Quadrate:', squares.join(', '));
console.log('Summe:', sum, 'Fibonacci(20):', fib);
print('JS_EXAMPLE_MATH_OK');
