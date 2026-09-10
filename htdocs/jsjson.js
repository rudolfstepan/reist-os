// Aufruf: js /htdocs/jsjson.js
// JSON ist hier nur Text im privaten Speicher, keine Konfigurationsdatei.
class Item {
    constructor(name, value) { this.name = name; this.value = value; }
    describe() { return this.name + ': ' + this.value; }
}
class CheckedItem extends Item {
    valid() { return Number.isInteger(this.value) && this.value >= 0; }
}
const item = new CheckedItem('Test', 42);
const encoded = JSON.stringify({system: 'REIST OS', item, enabled: true});
const copy = JSON.parse(encoded);
if (!(item instanceof Item) || !item.valid() || item.describe() !== 'Test: 42' ||
    copy.system !== 'REIST OS' || copy.item.value !== 42 || !copy.enabled) {
    throw Error('Klassen- oder JSON-Test fehlgeschlagen');
}
console.log(encoded);
print('JS_EXAMPLE_JSON_OK');
