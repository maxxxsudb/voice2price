import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('../src/recognition.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
const { recognizeFile, processOrders } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
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
      assert.equal(published[0].orderStatus, 'processing');
      assert.equal(JSON.parse(options.body).employee_id, 'employee-1');
      secondRequest();
      return pending;
    });
  await started;
  assert.equal(published.length, 1);
  finishGPT(Response.json({ order_items: [{ name: 'Бумага', quantity: 3 }], parser: 'rules',
    client: { client_id: 'c1', name: 'Ромашка', needs_review: false } }));
  await task;
  assert.equal(published[1].text, transcript.text);
  assert.equal(published[1].orderStatus, 'done');
  assert.equal(published[1].orderItems[0].quantity, 3);
  assert.equal(published[1].client.client_id, 'c1');
  assert.equal(published[1].parser, 'rules');
});

test('branch, engine and parser are sent; client comes with the transcript', async () => {
  const published = [];
  await recognizeFile(file(), 'branch-1', true, endpoints, item => published.push(item),
    async (url, options) => {
      if (url === '/recognize') {
        assert.equal(options.body.get('employee_id'), 'branch-1');
        assert.equal(options.body.get('engine'), 'gigaam');
        return Response.json({ ...transcript, engine: 'gigaam',
          client: { client_id: 'c2', name: 'Нурыев', needs_review: false } });
      }
      assert.equal(JSON.parse(options.body).parser, 'llm');
      return Response.json({ order_items: [], client: null });
    }, 'gigaam', 'llm');
  assert.equal(published[0].engine, 'gigaam');
  assert.equal(published[0].client.client_id, 'c2');
  assert.equal(published[1].client.client_id, 'c2');  // order response without a client keeps it
});

test('GPT network and HTTP errors retain transcript and timings', async () => {
  for (const fail of [() => { throw new Error('network failed'); }, () => Response.json({ error: 'GPT failed' }, { status: 502 })]) {
    const published = [];
    await recognizeFile(file(), null, true, endpoints, item => published.push(item),
      async url => url === '/recognize' ? Response.json(transcript) : fail());
    assert.equal(published.at(-1).status, 'success');
    assert.equal(published.at(-1).text, transcript.text);
    assert.deepEqual(published.at(-1).segments, transcript.segments_with_timings);
    assert.equal(published.at(-1).orderStatus, 'error');
    assert.ok(published.at(-1).orderError);
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

test('all transcripts of a batch go to one merge request with recording times', async () => {
  const results = [
    { fileId: 'a', fileName: '2026-08-23 21-37-42.mp3', text: 'бочок индейки', status: 'success', confidence: 0 },
    { fileId: 'b', fileName: 'b.mp3', text: '', status: 'success', confidence: 0 },
    { fileId: 'c', fileName: 'c.mp3', text: '', status: 'error', confidence: 0 },
    { fileId: 'd', fileName: 'd.mp3', text: 'два кило', status: 'success', confidence: 0 },
  ];
  let body;
  const orders = await processOrders(results, [{ id: 'd', name: 'd.mp3', lastModified: 123 }], 'branch-1',
    '/process-orders', async (url, options) => {
      body = JSON.parse(options.body);
      return Response.json({ orders: [{ message_ids: ['a', 'd'], order_items: [] }] });
    }, 'llm');
  assert.equal(body.employee_id, 'branch-1');
  assert.equal(body.parser, 'llm');
  assert.deepEqual(body.messages.map(m => [m.id, m.last_modified]), [['a', undefined], ['d', 123]]);
  assert.deepEqual(orders[0].message_ids, ['a', 'd']);
});

test('merge request errors are reported', async () => {
  await assert.rejects(processOrders(
    [{ fileId: 'a', fileName: 'a.mp3', text: 'x', status: 'success', confidence: 0 }], [], 'b', '/p',
    async () => Response.json({ error: 'Выберите филиал' }, { status: 400 })), /Выберите филиал/);
});
