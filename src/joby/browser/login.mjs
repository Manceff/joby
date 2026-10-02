// Ouvre le navigateur persistant de Joby pour que tu te connectes toi-même à tes sites.
// L'agent réutilisera ensuite ces sessions : il ne voit jamais tes mots de passe.
//
// Usage : node login.mjs <dossier-profil> <url> [url...]

import { createRequire } from 'node:module';
import path from 'node:path';

const careerOps = process.env.JOBY_CAREER_OPS;
const require = createRequire(path.join(careerOps, 'package.json'));
const { chromium } = require('playwright');

const [profileDir, ...urls] = process.argv.slice(2);

const context = await chromium.launchPersistentContext(profileDir, {
  headless: false,
  viewport: null,
  args: ['--start-maximized'],
});

const pages = context.pages();
for (const [i, url] of urls.entries()) {
  const page = i < pages.length ? pages[i] : await context.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
}

// On attend que tu fermes la fenêtre.
await new Promise((resolve) => context.on('close', resolve));
