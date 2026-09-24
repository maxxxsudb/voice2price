import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('../src/recognition.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
const { recognizeFile } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
const endpoints = { recognize: '/recognize', processOrder: '/process-order' };
const file = () => Object.assign(new File(['audio'], 'order.mp3'), { id: 'audio-1' });
const transcript = { text: 'Бумага три упаковки', segments_with_timings: [{ text: 'Бумага', startTime: '0s' }] };

test('transcript is published while GPT is still pending', async () => {
  const published = [];
  let finishGPT;
  const pending = new Promise(resolve => { finishGPT = resolve; });
  let secondRequest;
  const started = new Promise(resolve => { secondRequest = resolve; });
  const task = recognizeFile(file(), 'employee-1', true, endpoints, item => published.push(item),
    async (url, options) => {
      if (url === '/recognize') {
        assert.equal(options.body.has('process_llm'), false);
        return Response.json(transcript);
      }
      assert.equal(published[0].text, transcript.text);
      assert.equal(published[0].llmStatus, 'processing');
      assert.equal(JSON.parse(options.body).employee_id, 'employee-1');
      secondRequest();
      return pending;
    });
  await started;
  assert.equal(published.length, 1);
  finishGPT(Response.json({ order_items: [{ name: 'Бумага', quantity: 3 }] }));
  await task;
  assert.equal(published[1].text, transcript.text);
  assert.equal(published[1].llmStatus, 'done');
  assert.equal(published[1].orderItems[0].quantity, 3);
});

test('GPT network and HTTP errors retain transcript and timings', async () => {
  for (const fail of [() => { throw new Error('network failed'); }, () => Response.json({ error: 'GPT failed' }, { status: 502 })]) {
    const published = [];
    await recognizeFile(file(), null, true, endpoints, item => published.push(item),
      async url => url === '/recognize' ? Response.json(transcript) : fail());
    assert.equal(published.at(-1).status, 'success');
    assert.equal(published.at(-1).text, transcript.text);
    assert.deepEqual(published.at(-1).segments, transcript.segments_with_timings);
    assert.equal(published.at(-1).llmStatus, 'error');
    assert.ok(published.at(-1).llmError);
  }
});

test('disabled GPT and empty transcript never call order endpoint', async () => {
  for (const [enabled, text] of [[false, 'текст'], [true, '']]) {
    let calls = 0;
    await recognizeFile(file(), null, enabled, endpoints, () => {}, async () => {
      calls++;
      return Response.json({ text });
    });
    assert.equal(calls, 1);
  }
});

test('SpeechKit errors do not call GPT', async () => {
  const published = [];
  let calls = 0;
  await recognizeFile(file(), null, true, endpoints, item => published.push(item), async () => {
    calls++;
    return Response.json({ error: 'SpeechKit failed' }, { status: 500 });
  });
  assert.equal(calls, 1);
  assert.equal(published[0].status, 'error');
  assert.equal(published[0].error, 'SpeechKit failed');
});
