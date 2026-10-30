import express from 'express';
import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { createServer as createViteServer } from 'vite';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;
const BOT_API_BASE = 'http://127.0.0.1:5005';

app.use(express.json({ limit: '10mb' }));

// -------------------------------------------------------------
// Python Bot Supervisor (bot.py running 24/7)
// -------------------------------------------------------------
let botProcess: ChildProcess | null = null;
const processLogs: Array<{ id: number; text: string; time: string; type: 'stdout' | 'stderr' | 'system' }> = [];
let logIdCounter = 1;

function addProcessLog(text: string, type: 'stdout' | 'stderr' | 'system' = 'stdout') {
  const time = new Date().toLocaleTimeString('ar-EG', { hour12: false });
  processLogs.push({ id: logIdCounter++, text: text.trimEnd(), time, type });
  if (processLogs.length > 200) {
    processLogs.shift();
  }
}

function startBotProcess() {
  if (botProcess && !botProcess.killed) return;

  addProcessLog('[Supervisor] Starting Dahiha Thanwi Telegram Bot Engine...', 'system');
  try {
    botProcess = spawn('python3', ['bot.py'], {
      cwd: __dirname,
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    botProcess.stdout?.on('data', (d) => {
      const msg = d.toString();
      addProcessLog(msg, 'stdout');
      console.log(`[Bot stdout] ${msg.trimEnd()}`);
    });

    botProcess.stderr?.on('data', (d) => {
      const msg = d.toString();
      addProcessLog(msg, 'stderr');
      console.error(`[Bot stderr] ${msg.trimEnd()}`);
    });

    botProcess.on('close', (code) => {
      addProcessLog(`[Supervisor] Bot process closed with code ${code}. Auto-restarting in 3s...`, 'system');
      botProcess = null;
      setTimeout(startBotProcess, 3000);
    });
  } catch (err: any) {
    addProcessLog(`[Supervisor] Failed to launch bot: ${err.message}`, 'stderr');
  }
}

// Start bot daemon
startBotProcess();

// -------------------------------------------------------------
// Telemetry & Status API
// -------------------------------------------------------------
app.get('/api/bot/status', async (req, res) => {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);
    const resp = await fetch(`${BOT_API_BASE}/api/status`, { signal: controller.signal });
    clearTimeout(timeout);

    if (resp.ok) {
      const data = await resp.json();
      return res.json({
        ...data,
        process_alive: botProcess !== null && !botProcess.killed,
      });
    }
  } catch (e) {}

  res.json({
    status: botProcess !== null && !botProcess.killed ? 'online' : 'connecting',
    process_alive: botProcess !== null && !botProcess.killed,
    bot: {
      id: 9170444919,
      username: 'Dahiha_Thanwi_bot',
      first_name: 'دحيحة ثانوي',
    },
    token: '9170444919:AAFn5ukIgdNxNZzqsZ8eoYN0RCF_CDTH778',
    uptime_seconds: 0,
    metrics: {
      deleted_messages: 0,
      total_invites: 0,
      warnings_sent: 0,
      links_blocked: 0,
      spam_blocked: 0,
      whispers_sent: 0,
      active_groups: 1,
    },
  });
});

app.get('/api/bot/groups', async (req, res) => {
  try {
    const resp = await fetch(`${BOT_API_BASE}/api/groups`);
    if (resp.ok) return res.json(await resp.json());
  } catch (e) {}
  res.json({ groups: [] });
});

app.get('/api/bot/logs', async (req, res) => {
  try {
    const resp = await fetch(`${BOT_API_BASE}/api/logs?limit=${req.query.limit || 50}`);
    if (resp.ok) return res.json(await resp.json());
  } catch (e) {}
  res.json({ logs: [] });
});

app.get('/api/bot/process-logs', (req, res) => {
  res.json({ logs: processLogs });
});

// -------------------------------------------------------------
// Vite Dev Server / Static Asset Mounting
// -------------------------------------------------------------
async function bootstrap() {
  const isProd = process.env.NODE_ENV === 'production';

  if (!isProd) {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.join(__dirname, 'dist')));
    app.get('*', (req, res) => {
      res.sendFile(path.join(__dirname, 'dist', 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Dahiha Thanwi Bot Server active on port ${PORT}`);
  });
}

bootstrap().catch((err) => {
  console.error('Failed to start server:', err);
});
