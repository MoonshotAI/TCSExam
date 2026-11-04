import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultState, selectOption, generateCommands } from '../src/get-started.js';
const repository = { cloneUrl: 'https://example.org/team/TCSExam.git', ref: 'release/test' };

test('suite changes restore its protocol default and protocol remains selectable', () => {
  assert.equal(selectOption(defaultState, 'suite', 'full').protocol, 'online');
  assert.equal(selectOption({ ...defaultState, protocol: 'online' }, 'suite', 'lite').protocol, 'offline');
  assert.equal(selectOption({ ...defaultState, suite: 'full' }, 'protocol', 'offline').protocol, 'offline');
});

for (const suite of ['lite', 'full']) for (const protocol of ['offline', 'online']) for (const agent of ['kimi-code', 'claude-code', 'codex', 'grok-build']) {
  test(`${suite}/${protocol}/${agent} generates a complete, explicit selection`, () => {
    const commands = generateCommands({ suite, protocol, agent }, repository);
    assert.match(commands.install, /git clone --branch 'release\/test' -- 'https:\/\/example.org\/team\/TCSExam.git'/);
    assert.match(commands.configure, new RegExp(`TCSEXAM_AGENT="${agent}"`));
    for (const name of ['API_BASE_URL', 'MODEL', 'API_KEY']) assert.ok(commands.configure.includes(`TCSEXAM_${name}=`));
    for (const operation of ['build', 'doctor', 'run']) {
      assert.ok(commands.run.includes(`tcsexam ${operation} --suite ${suite} --solver-protocol ${protocol}`));
    }
    assert.ok(!commands.run.includes('--task '));
    assert.equal((commands.run.match(new RegExp(`--agent ${agent}`, 'g')) || []).length, 2);
    assert.equal((commands.run.match(/--backend-plan "\$TCSEXAM_BACKEND_PLAN"/g) || []).length, protocol === 'online' ? 2 : 0);
    assert.equal(commands.install.includes('runtime,backend'), protocol === 'online');
    for (const name of ['BASE_URL', 'TOKEN_ID', 'TOKEN_SECRET', 'ARCHIVE_TOKEN', 'BACKEND_PLAN']) {
      assert.equal(commands.configure.includes(`TCSEXAM_${name}=`), protocol === 'online');
    }
    if (protocol === 'online') assert.ok(commands.run.includes(`match ${suite.toUpperCase()} / Online`));
  });
}

test('provider endpoint and backend match the selected harness', () => {
  assert.match(generateCommands({ agent: 'claude-code' }, repository).configure, /https:\/\/YOUR_ANTHROPIC_PROVIDER.example"/);
  for (const agent of ['codex', 'grok-build']) assert.match(generateCommands({ agent }, repository).configure, /\.example\/v1"/);
  assert.match(generateCommands({ agent: 'grok-build' }, repository).configure, /TCSEXAM_GROK_API_BACKEND="responses"/);
});

test('clone inputs are shell quoted and unsupported selections fail', () => {
  assert.ok(generateCommands(defaultState, { cloneUrl: "https://example.org/a'b.git", ref: '$(touch secret)' }).install.includes("--branch '$(touch secret)'"));
  assert.throws(() => generateCommands({ agent: 'other' }, repository), /Unsupported/);
});
