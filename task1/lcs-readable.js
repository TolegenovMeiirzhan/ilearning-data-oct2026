const argumentsToCheck = process.argv.slice(2);
const firstString = argumentsToCheck[0] || '';
let answer = '';

search: for (let length = firstString.length; length >= 0; length--) {
  for (let start = 0; start + length <= firstString.length; start++) {
    const candidate = firstString.slice(start, start + length);
    if (argumentsToCheck.every(text => text.includes(candidate))) {
      answer = candidate;
      break search;
    }
  }
}
console.log(answer);
