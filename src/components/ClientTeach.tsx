import { useEffect, useState } from 'react';
import { API } from '../api';
import type { ClientMatch } from '../types';

// Менеджер подтверждает клиента один раз — сказанное сохраняется в словарь как
// сокращение (категория «Клиент»), и в следующий раз клиент определится сам.

interface BranchClient { id: string; name: string; public_name?: string | null }

let cache: { employeeId: string; clients: BranchClient[] } | null = null;

async function branchClients(employeeId: string): Promise<BranchClient[]> {
  if (cache?.employeeId === employeeId) return cache.clients;
  const response = await fetch(API.employeeClients(employeeId));
  if (!response.ok) throw new Error('Не удалось загрузить клиентов филиала');
  const data = await response.json();
  cache = { employeeId, clients: Array.isArray(data.clients) ? data.clients : [] };
  return cache.clients;
}

// «дидайна бугульма мира пятьдесят» -> «дидайна»: сокращение — первые слова до адреса
export function suggestedShortForm(said: string) {
  return said.split(/\s+/).filter(Boolean).slice(0, 1).join(' ');
}

export default function ClientTeach({ client, employeeId }: { client: ClientMatch; employeeId: string }) {
  const [open, setOpen] = useState(false);
  const [clients, setClients] = useState<BranchClient[]>([]);
  const [query, setQuery] = useState('');
  const [chosen, setChosen] = useState<string>(client.client_id ?? client.candidates[0]?.id ?? '');
  const [shortForm, setShortForm] = useState(suggestedShortForm(client.said || ''));
  const [state, setState] = useState<{ saving?: boolean; done?: string; error?: string }>({});

  useEffect(() => {
    if (!open) return;
    branchClients(employeeId).then(setClients).catch(error => setState({ error: error.message }));
  }, [open, employeeId]);

  const needle = query.trim().toLowerCase();
  const candidateIds = new Set(client.candidates.map(c => c.id));
  const listed = [
    ...client.candidates.map(c => ({ id: c.id, name: c.name })),
    ...clients.filter(c => !candidateIds.has(String(c.id))
      && (!needle || `${c.name} ${c.public_name ?? ''}`.toLowerCase().includes(needle))).slice(0, needle ? 20 : 0),
  ];
  const target = clients.find(c => String(c.id) === chosen) ?? client.candidates.find(c => c.id === chosen);

  const save = async () => {
    if (!target || !shortForm.trim()) return;
    setState({ saving: true });
    try {
      const response = await fetch(API.employeeDictionary(employeeId), {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ original: target.name, variant: shortForm.trim(), category: 'client', item_id: target.id }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || `Ошибка ${response.status}`);
      cache = null;
      setState({ done: `Запомнено: «${shortForm.trim()}» → ${target.name}` });
    } catch (error) {
      setState({ error: error instanceof Error ? error.message : 'Не удалось сохранить' });
    }
  };

  if (state.done) return <p className="mt-2 text-emerald-300 text-xs">{state.done}</p>;
  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)}
        className="mt-2 text-cyan-200 underline hover:text-cyan-100 text-xs">
        {client.client_id ? 'Подтвердить или выбрать другого и запомнить' : 'Указать клиента и запомнить'}
      </button>
    );
  }
  return (
    <div className="mt-3 space-y-2 rounded-lg bg-black/30 p-3">
      <label className="block text-xs text-gray-100">
        Как назвали клиента (сохранится в словарь)
        <input value={shortForm} onChange={e => setShortForm(e.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900" />
      </label>
      <label className="block text-xs text-gray-100">
        Клиент
        <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Поиск по фамилии или названию"
          className="mt-1 w-full rounded-md border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900 placeholder-gray-500" />
      </label>
      <div className="max-h-40 overflow-y-auto space-y-1" role="radiogroup" aria-label="Клиент">
        {listed.map(c => (
          <label key={c.id} className="flex items-center gap-2 text-sm text-gray-100 cursor-pointer">
            <input type="radio" name={`client-${client.said}`} checked={chosen === String(c.id)}
              onChange={() => setChosen(String(c.id))} className="accent-cyan-300" />
            {c.name}
          </label>
        ))}
        {listed.length === 0 && <p className="text-gray-300 text-xs">Начните вводить фамилию</p>}
      </div>
      <div className="flex items-center gap-3">
        <button type="button" onClick={save} disabled={!target || !shortForm.trim() || state.saving}
          className="rounded-md bg-cyan-300 px-3 py-1.5 text-sm font-medium text-slate-950 hover:bg-cyan-200 disabled:bg-gray-200 disabled:text-gray-700">
          Запомнить
        </button>
        <button type="button" onClick={() => setOpen(false)} className="text-gray-200 text-sm hover:text-white">Отмена</button>
        {state.error && <span className="text-amber-200 text-xs">{state.error}</span>}
      </div>
    </div>
  );
}
