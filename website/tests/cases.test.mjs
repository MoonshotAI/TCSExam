import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { hammingDistance, nearestCodewords } from '../src/binary-code-case.js';

const code = JSON.parse(await readFile(new URL('../public/paper/binary-code.json', import.meta.url), 'utf8'));
const { words } = code;
const flip = (word, positions) => [...word].map((bit, i) => positions.includes(i) ? String(1 - Number(bit)) : bit).join('');

test('All submitted codewords are distinct, length 22, and at least 10 bits apart', () => {
  assert.equal(new Set(words).size, 64);
  assert(words.every(word => /^[01]{22}$/.test(word)));
  const distances = {};
  let pairs = 0;
  words.forEach((a, i) => words.slice(i + 1).forEach(b => {
    const d = hammingDistance(a, b);
    distances[d] = (distances[d] || 0) + 1;
    pairs++;
  }));
  assert.equal(pairs, 2016);
  assert.deepEqual(distances, code.pair_distances);
  assert.equal(Math.min(...Object.keys(distances).map(Number)), 10);
  // Disjoint radius-four Hamming balls establish correction for every pattern.
  assert(2 * code.correctable_bit_flips < code.minimum_distance);
});

test('Every codeword decodes correctly with zero through four flipped bits', () => {
  words.forEach((word, index) => {
    for (let start = 0; start < 22; start++) {
      for (let count = 0; count <= 4; count++) {
        const received = flip(word, Array.from({ length: count }, (_, i) => (start + i * 5) % 22));
        assert.deepEqual(nearestCodewords(words, received), { distance: count, indices: [index] });
      }
    }
  });
});

test('Five-flip ties and decoding to a different word are not reported as recovery', () => {
  const a = words[0];
  const other = words.findIndex(word => hammingDistance(a, word) === 10);
  const differences = [...a].flatMap((bit, i) => bit === words[other][i] ? [] : [i]);
  const tie = nearestCodewords(words, flip(a, differences.slice(0, 5)));
  assert.equal(tie.distance, 5);
  assert(tie.indices.includes(0) && tie.indices.includes(other));
  assert.deepEqual(nearestCodewords(words, flip(a, differences)), { distance: 0, indices: [other] });
});
