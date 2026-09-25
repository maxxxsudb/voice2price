import { useEffect, useState } from 'react';
import { API } from '../api';
import type { CatalogValidation, ValidationIssue } from '../types';

interface Props {
  employeeId: string;
  compact?: boolean;       // на экране загрузки: только итог и ошибки
  refreshKey?: number;     // меняется после импорта — проверить заново
  onOpen?: () => void;     // перейти к справочнику филиала
}

const LEVEL = {
  error: { title: 'Ошибка', box: 'border-red-500/40 bg-red-950/60 text-red-100' },
  warning: { title: 'Предупреждение', box: 'border-amber-500/40 bg-amber-950/60 text-amber-100' },
  info: { title: 'Справка', box: 'border-white/10 bg-gray-900 text-gray-100' },
};

// Позиции, название которых целиком входит в название другой: по нему подходят обе.
function Overlaps({ issue, open }: { issue: ValidationIssue; open?: boolean }) {
  return (
    <details open={open} className="mt-2">
      <summary className="cursor-pointer">Показать пересечения ({issue.details?.length ?? 0})</summary>
      <ul className="mt-2 space-y-1.5">
        {issue.details?.map(row => (
          <li key={row.product.id}>
            <span className="font-medium">{row.product.name.trim()}</span>
            <ul className="pl-4 opacity-90">
              {row.also.map(other => (
                <li key={other.product.id}>
                  ⟷ {other.product.name.trim()}
                  {other.say && <span className="opacity-80"> — отличие: «{other.say}»</span>}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </details>
  );
}

// Проблемы справочника, из-за которых голосовой заказ нельзя разобрать однозначно:
// показываем заранее, а не в каждом заказе.
export default function CatalogValidationPanel({ employeeId, compact, refreshKey, onOpen }: Props) {
  const [report, setReport] = useState<CatalogValidation | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setError('');
    fetch(API.employeeNomenclatureValidation(employeeId))
      .then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Не удалось проверить справочник');
        return data;
      })
      .then(data => { if (!cancelled) setReport(data); })
      .catch(err => { if (!cancelled) setError(err instanceof Error ? err.message : 'Ошибка проверки'); });
    return () => { cancelled = true; };
  }, [employeeId, refreshKey]);

  if (error) return <p className="rounded-xl bg-gray-900 p-3 text-sm text-gray-100">Проверка справочника: {error}</p>;
  if (!report) return null;
  const { error: errors, warning } = report.counts;
  const overlaps = report.issues.find(issue => issue.kind === 'overlapping_products');
  const shown = report.issues.filter(issue => !compact || issue.level === 'error');

  if (compact && errors + warning === 0) return null;
  return (
    <div className={`rounded-xl border p-4 text-sm ${LEVEL[errors ? 'error' : warning ? 'warning' : 'info'].box}`}>
      <p className="font-semibold">
        {errors + warning === 0
          ? `Справочник проверен: ${report.catalog_size} позиций, проблем не найдено`
          : `Проблемы справочника филиала: ошибок ${errors}, предупреждений ${warning}`}
      </p>
      {compact && errors > 0 && (
        <p className="mt-1">Позиции с ошибками всегда уйдут на ручную проверку.</p>
      )}
      {compact && overlaps && (
        <div className="mt-2">
          <p>{overlaps.message}</p>
          <Overlaps issue={overlaps} />
        </div>
      )}
      {compact && onOpen && (
        <button className="mt-2 underline" onClick={onOpen}>Открыть справочник</button>
      )}
      {shown.length > 0 && (
        <ul className="mt-3 space-y-2">
          {shown.map((issue, index) => (
            <li key={`${issue.kind}-${index}`} className={`rounded-lg border p-3 ${LEVEL[issue.level].box}`}>
              <p><strong>{LEVEL[issue.level].title}:</strong> {issue.message}</p>
              {issue.details ? <Overlaps issue={issue} /> : issue.items.length > 0 && (
                <ul className="mt-1 list-disc pl-5">
                  {issue.items.map(item => (
                    <li key={item.id}>{item.name} <span className="opacity-70">(ID: {item.id})</span></li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
