export default function Instructions() {
  return (
    <div className="space-y-6">
      {/* Quick Start */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <h2 className="text-white font-bold text-xl mb-4 flex items-center gap-2">
          <i className="fas fa-rocket text-yellow-400"></i>
          Быстрый старт
        </h2>
        <div className="space-y-4">
          <Step
            number={1}
            title="Получите API-ключ Яндекс SpeechKit"
            description={
              <>
                Перейдите на{' '}
                <a href="https://console.cloud.yandex.ru/" target="_blank" rel="noopener noreferrer" className="text-yellow-400 underline hover:text-yellow-300">
                  console.cloud.yandex.ru
                </a>
                . Создайте сервисный аккаунт с ролью <code className="bg-white/10 px-1.5 py-0.5 rounded text-yellow-300">editor</code>.
                Создайте API-ключ.
              </>
            }
          />
          <Step
            number={2}
            title="Установите Python и зависимости"
            description={
              <>
                Нужен Python 3.8+. Установите библиотеки:
                <CodeBlock code="pip install requests pydub rapidfuzz" />
                Также нужен <strong>ffmpeg</strong> (для конвертации MP3):
              </>
            }
            extra={
              <div className="mt-2 space-y-1 text-sm text-gray-400">
                <p>• <strong>macOS:</strong> <code className="bg-white/10 px-1 rounded">brew install ffmpeg</code></p>
                <p>• <strong>Ubuntu/Debian:</strong> <code className="bg-white/10 px-1 rounded">sudo apt install ffmpeg</code></p>
                <p>• <strong>Windows:</strong> скачайте с <a href="https://ffmpeg.org/download.html" target="_blank" rel="noopener noreferrer" className="text-yellow-400 underline">ffmpeg.org</a> и добавьте в PATH</p>
              </div>
            }
          />
          <Step
            number={3}
            title="Скачайте скрипт"
            description={
              <>
                Перейдите на вкладку <strong>"Python скрипт"</strong>, настройте параметры и нажмите
                <strong> "Скачать mp3_recognizer.py"</strong>.
              </>
            }
          />
          <Step
            number={4}
            title="Подготовьте файлы"
            description={
              <>
                Создайте папку <code className="bg-white/10 px-1.5 py-0.5 rounded text-yellow-300">audio_files</code> и положите туда ваши MP3 файлы.
              </>
            }
          />
          <Step
            number={5}
            title="Запустите"
            description={<>Запустите скрипт:</>}
            extra={
              <CodeBlock code="python mp3_recognizer.py" />
            }
          />
        </div>
      </div>

      {/* Architecture */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <h3 className="text-white font-bold text-lg mb-4 flex items-center gap-2">
          <i className="fas fa-diagram-project text-cyan-400"></i>
          Что делает скрипт
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white/5 rounded-xl p-4">
            <h4 className="text-white font-medium text-sm mb-2 flex items-center gap-2">
              <i className="fas fa-1 text-cyan-400 w-5 h-5 rounded-full bg-cyan-500/20 flex items-center justify-center text-xs"></i>
              Анализ файлов
            </h4>
            <p className="text-gray-400 text-xs">
              Сканирует папку, находит MP3/WAV/OGG, анализирует длительность, громкость, процент тишины.
            </p>
          </div>
          <div className="bg-white/5 rounded-xl p-4">
            <h4 className="text-white font-medium text-sm mb-2 flex items-center gap-2">
              <i className="fas fa-2 text-cyan-400 w-5 h-5 rounded-full bg-cyan-500/20 flex items-center justify-center text-xs"></i>
              Конвертация
            </h4>
            <p className="text-gray-400 text-xs">
              Через pydub + ffmpeg конвертирует в PCM 16kHz mono 16bit — формат, который принимает SpeechKit.
            </p>
          </div>
          <div className="bg-white/5 rounded-xl p-4">
            <h4 className="text-white font-medium text-sm mb-2 flex items-center gap-2">
              <i className="fas fa-3 text-cyan-400 w-5 h-5 rounded-full bg-cyan-500/20 flex items-center justify-center text-xs"></i>
              Распознавание
            </h4>
            <p className="text-gray-400 text-xs">
              Отправляет PCM на API SpeechKit, получает текст. Обрабатывает ошибки.
            </p>
          </div>
          <div className="bg-white/5 rounded-xl p-4">
            <h4 className="text-white font-medium text-sm mb-2 flex items-center gap-2">
              <i className="fas fa-4 text-cyan-400 w-5 h-5 rounded-full bg-cyan-500/20 flex items-center justify-center text-xs"></i>
              Поиск номенклатуры
            </h4>
            <p className="text-gray-400 text-xs">
              Ищет ваши термины в тексте. Поддерживает нечёткий поиск (rapidfuzz) для учёта ошибок распознавания.
            </p>
          </div>
        </div>
      </div>

      {/* Output */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <h3 className="text-white font-bold text-lg mb-4 flex items-center gap-2">
          <i className="fas fa-file-export text-green-400"></i>
          Что получится на выходе
        </h3>
        <div className="space-y-3">
          <div className="bg-white/5 rounded-xl p-4 flex items-start gap-3">
            <i className="fas fa-file-code text-yellow-400 mt-1"></i>
            <div>
              <p className="text-white font-medium text-sm">results.json</p>
              <p className="text-gray-400 text-xs">Полные данные: текст, номенклатура, метаданные, время обработки</p>
            </div>
          </div>
          <div className="bg-white/5 rounded-xl p-4 flex items-start gap-3">
            <i className="fas fa-file-lines text-blue-400 mt-1"></i>
            <div>
              <p className="text-white font-medium text-sm">results.txt</p>
              <p className="text-gray-400 text-xs">Читаемый текст с разделителями между файлами</p>
            </div>
          </div>
          <div className="bg-white/5 rounded-xl p-4 flex items-start gap-3">
            <i className="fas fa-file-csv text-green-400 mt-1"></i>
            <div>
              <p className="text-white font-medium text-sm">nomenclature_matches.csv</p>
              <p className="text-gray-400 text-xs">Таблица всех найденных совпадений номенклатуры — удобно для Excel</p>
            </div>
          </div>
        </div>
      </div>

      {/* FAQ */}
      <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
        <h3 className="text-white font-bold text-lg mb-4 flex items-center gap-2">
          <i className="fas fa-circle-question text-purple-400"></i>
          Частые вопросы
        </h3>
        <div className="space-y-4">
          <FaqItem
            question="Это работает на Windows?"
            answer="Да. Нужен Python (скачайте с python.org), ffmpeg (добавьте в PATH), и зависимости через pip. Всё."
          />
          <FaqItem
            question="А на Mac?"
            answer="Да. brew install ffmpeg, pip install ... — и работает."
          />
          <FaqItem
            question="А в Docker?"
            answer={
              <>
                Можно. Пример Dockerfile:
                <CodeBlock code={`FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg
RUN pip install requests pydub rapidfuzz
COPY mp3_recognizer.py .
COPY audio_files/ ./audio_files/
CMD ["python", "mp3_recognizer.py"]`} />
              </>
            }
          />
          <FaqItem
            question="Сколько стоит SpeechKit?"
            answer="Есть бесплатный лимит (≈10 часов/месяц). Дальше ~0.15₽ за 15 секунд аудио. Для тестов хватит бесплатно."
          />
          <FaqItem
            question="Что если распознаёт плохо?"
            answer="Попробуйте: 1) модель general:rc, 2) проверьте громкость (если < -40 dBFS — тихо), 3) убедитесь что нет фонового шума, 4) используйте нечёткий поиск номенклатуры."
          />
          <FaqItem
            question="Можно ли запустить прямо из браузера?"
            answer="Нет. SpeechKit API не поддерживает CORS — запросы из браузера блокируются. Нужен бэкенд (Python, Node.js, etc.)."
          />
        </div>
      </div>

      {/* Troubleshooting */}
      <div className="bg-red-500/5 backdrop-blur-sm rounded-2xl border border-red-500/20 p-6">
        <h3 className="text-white font-bold text-lg mb-4 flex items-center gap-2">
          <i className="fas fa-bug text-red-400"></i>
          Решение проблем
        </h3>
        <div className="space-y-3 text-sm">
          <div className="bg-black/20 rounded-lg p-3">
            <p className="text-red-300 font-mono text-xs mb-1">❌ FileNotFoundError: ffmpeg</p>
            <p className="text-gray-400">Установите ffmpeg и добавьте в PATH. Перезапустите терминал.</p>
          </div>
          <div className="bg-black/20 rounded-lg p-3">
            <p className="text-red-300 font-mono text-xs mb-1">❌ HTTP 401 Unauthorized</p>
            <p className="text-gray-400">Неверный API-ключ. Проверьте, что скопировали его полностью.</p>
          </div>
          <div className="bg-black/20 rounded-lg p-3">
            <p className="text-red-300 font-mono text-xs mb-1">❌ Пустой текст при распознавании</p>
            <p className="text-gray-400">Проверьте: 1) в файле есть речь, 2) громкость нормальная, 3) язык указан верно.</p>
          </div>
          <div className="bg-black/20 rounded-lg p-3">
            <p className="text-red-300 font-mono text-xs mb-1">❌ Номенклатура не находится</p>
            <p className="text-gray-400">Включите нечёткий поиск и понизьте порог до 70-80%. SpeechKit может транскрибировать слова с ошибками.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Step({ number, title, description, extra }: {
  number: number;
  title: string;
  description: React.ReactNode;
  extra?: React.ReactNode;
}) {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center text-black font-bold text-sm">
        {number}
      </div>
      <div className="flex-1">
        <h4 className="text-white font-medium mb-1">{title}</h4>
        <p className="text-gray-400 text-sm">{description}</p>
        {extra}
      </div>
    </div>
  );
}

function CodeBlock({ code }: { code: string }) {
  return (
    <div className="mt-2 bg-black/30 rounded-lg p-3 font-mono text-xs text-green-300 overflow-x-auto">
      <code>{code}</code>
    </div>
  );
}

function FaqItem({ question, answer }: { question: string; answer: React.ReactNode }) {
  return (
    <details className="group bg-white/5 rounded-xl overflow-hidden">
      <summary className="px-4 py-3 cursor-pointer text-white font-medium text-sm flex items-center justify-between hover:bg-white/5 transition-colors">
        <span>{question}</span>
        <i className="fas fa-chevron-down text-gray-400 text-xs group-open:rotate-180 transition-transform"></i>
      </summary>
      <div className="px-4 pb-3 text-gray-400 text-sm">
        {answer}
      </div>
    </details>
  );
}
