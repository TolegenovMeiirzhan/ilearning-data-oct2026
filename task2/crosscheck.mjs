import { createHash } from 'node:crypto';
import { readdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';

const [directory, suppliedEmail] = process.argv.slice(2);
if (!directory || !suppliedEmail || /\s/u.test(suppliedEmail)) {
  console.error('Usage: node crosscheck.mjs EXTRACTED_DIRECTORY REGISTRATION_EMAIL');
  process.exit(2);
}
const sha3 = bytes => createHash('sha3-256').update(bytes).digest('hex');
const entries = (await readdir(directory, { withFileTypes: true })).filter(entry => entry.isFile());
if (entries.length !== 256) throw new Error(`Expected 256 files, found ${entries.length}`);
const rows = [];
for (const entry of entries) {
  const digest = sha3(await readFile(join(directory, entry.name)));
  let product = 1n;
  for (const digit of digest) product *= BigInt(parseInt(digit, 16) + 1);
  rows.push({ file: entry.name, sha3_256: digest, product });
}
rows.sort((a, b) => a.product < b.product ? -1 : a.product > b.product ? 1 : 0);
const email = suppliedEmail.toLowerCase();
const result = sha3(rows.map(row => row.sha3_256).join('') + email);
console.log(JSON.stringify({
  registration_email_lowercase: email,
  file_count: rows.length,
  unique_sorting_keys: new Set(rows.map(row => row.product.toString())).size,
  answer_sha3_256: result,
  sorted_files: rows.map(row => ({ ...row, product: row.product.toString() })),
}, null, 2));
