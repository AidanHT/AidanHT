const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');

let width, height, dpr;
function resize() {
  dpr = Math.min(window.devicePixelRatio || 1, 2);
  width = Math.floor(window.innerWidth);
  height = Math.floor(window.innerHeight);
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  canvas.style.width = width + 'px';
  canvas.style.height = height + 'px';
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
window.addEventListener('resize', resize);
resize();

// HUD
const scoreEl = document.getElementById('score');
const livesEl = document.getElementById('lives');
const waveEl = document.getElementById('wave');

// Input
const keys = { left: false, right: false, shoot: false };
window.addEventListener('keydown', (e) => {
  if (e.code === 'ArrowLeft' || e.code === 'KeyA') keys.left = true;
  if (e.code === 'ArrowRight' || e.code === 'KeyD') keys.right = true;
  if (e.code === 'Space') keys.shoot = true;
  if (e.code === 'Enter' && game.over) startGame();
});
window.addEventListener('keyup', (e) => {
  if (e.code === 'ArrowLeft' || e.code === 'KeyA') keys.left = false;
  if (e.code === 'ArrowRight' || e.code === 'KeyD') keys.right = false;
  if (e.code === 'Space') keys.shoot = false;
});

// Utils
function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
function rand(min, max) { return Math.random() * (max - min) + min; }
function chance(p) { return Math.random() < p; }

// Game objects
const game = {
  over: false,
  score: 0,
  lives: 3,
  wave: 1,
  time: 0,
};

const player = {
  x: 0,
  y: 0,
  width: 44,
  height: 18,
  speed: 420,
  cooldown: 0,
};

let bullets = [];
let enemies = [];
let particles = [];
let stars = [];

function initStars() {
  stars = Array.from({ length: 180 }, () => ({
    x: rand(0, width),
    y: rand(0, height),
    z: rand(0.2, 1),
    s: rand(0.5, 1.8),
  }));
}

function startGame() {
  game.over = false;
  game.score = 0;
  game.lives = 3;
  game.wave = 1;
  game.time = 0;
  player.x = width / 2;
  player.y = height - 80;
  player.cooldown = 0;
  bullets = [];
  enemies = [];
  particles = [];
  initStars();
}

startGame();

// Rendering helpers
function drawShip(x, y, color = '#7aa2f7') {
  ctx.save();
  ctx.translate(x, y);
  ctx.fillStyle = color;
  ctx.strokeStyle = '#0ea5e9';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(-22, 9);
  ctx.lineTo(0, -9);
  ctx.lineTo(22, 9);
  ctx.lineTo(14, 9);
  ctx.lineTo(10, 4);
  ctx.lineTo(-10, 4);
  ctx.lineTo(-14, 9);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

function drawEnemy(x, y, t) {
  ctx.save();
  ctx.translate(x, y);
  const pulse = Math.sin(t * 6) * 0.5 + 0.5;
  ctx.fillStyle = `hsl(${220 + pulse * 100}, 90%, 60%)`;
  ctx.strokeStyle = 'rgba(0,0,0,0.5)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(0, 0, 16 + pulse * 2, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(-8, 0);
  ctx.lineTo(8, 0);
  ctx.stroke();
  ctx.restore();
}

function spawnEnemy() {
  const speed = 70 + game.wave * 10 + rand(-10, 10);
  enemies.push({
    x: rand(30, width - 30),
    y: -20,
    vy: speed,
    hp: 2 + Math.floor(game.wave / 2),
    t: 0,
    zigzag: rand(0.8, 1.6),
    off: rand(0, Math.PI * 2),
  });
}

function shoot() {
  if (player.cooldown > 0) return;
  player.cooldown = 180 - Math.min(120, game.wave * 5);
  bullets.push({ x: player.x - 8, y: player.y - 14, vy: -560, r: 3 });
  bullets.push({ x: player.x + 8, y: player.y - 14, vy: -560, r: 3 });
  // muzzle flash particles
  for (let i = 0; i < 6; i++) {
    particles.push({
      x: player.x, y: player.y - 16,
      vx: rand(-80, 80), vy: rand(-200, -80), life: rand(120, 240),
      color: 'rgba(255, 255, 255, 0.9)'
    });
  }
}

function explode(x, y, color = '#93c5fd') {
  for (let i = 0; i < 24; i++) {
    const a = rand(0, Math.PI * 2);
    const s = rand(80, 320);
    particles.push({
      x, y,
      vx: Math.cos(a) * s,
      vy: Math.sin(a) * s,
      life: rand(240, 600),
      color: color,
    });
  }
}

function rectsOverlap(ax, ay, aw, ah, bx, by, bw, bh) {
  return ax < bx + bw && ax + aw > bx && ay < by + bh && ay + ah > by;
}

let last = performance.now();
function loop(now) {
  const dt = Math.min(32, now - last) / 1000; // seconds
  last = now;
  update(dt);
  render(now / 1000);
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);

function update(dt) {
  if (game.over) return;
  game.time += dt;

  // Update stars parallax
  if (stars.length === 0) initStars();
  for (const s of stars) {
    s.y += s.z * 60 * dt * (1 + game.wave * 0.05);
    if (s.y > height) { s.y = -2; s.x = rand(0, width); s.z = rand(0.2, 1); }
  }

  // Player movement
  const accel = 900;
  if (!player.vx) player.vx = 0;
  if (keys.left) player.vx -= accel * dt;
  if (keys.right) player.vx += accel * dt;
  player.vx *= 0.86;
  player.x = clamp(player.x + player.vx * dt, 28, width - 28);

  // Shooting
  if (keys.shoot) shoot();
  if (player.cooldown > 0) player.cooldown -= 1000 * dt;

  // Bullets
  for (const b of bullets) b.y += b.vy * dt;
  bullets = bullets.filter(b => b.y > -30);

  // Enemy spawn rate increases each wave
  const spawnRate = Math.max(0.4, 1.2 - game.wave * 0.06);
  if (chance(dt / spawnRate)) spawnEnemy();

  // Enemies
  for (const e of enemies) {
    e.t += dt;
    e.y += e.vy * dt * 0.6;
    e.x += Math.sin(e.off + e.t * e.zigzag) * 60 * dt;
  }
  enemies = enemies.filter(e => e.y < height + 40);

  // Collisions: bullets vs enemies
  for (const e of enemies) {
    for (const b of bullets) {
      if (rectsOverlap(b.x - 3, b.y - 3, 6, 6, e.x - 14, e.y - 14, 28, 28)) {
        e.hp -= 1; b.y = -9999; // remove bullet
        if (e.hp <= 0) {
          game.score += 10 + game.wave * 2;
          explode(e.x, e.y);
          e.y = height + 9999; // remove enemy
        }
      }
    }
  }

  // Enemies hitting player
  for (const e of enemies) {
    if (rectsOverlap(player.x - 20, player.y - 9, 40, 18, e.x - 14, e.y - 14, 28, 28)) {
      explode(player.x, player.y, '#fca5a5');
      e.y = height + 9999;
      game.lives -= 1;
      livesEl.classList.add('flash');
      setTimeout(() => livesEl.classList.remove('flash'), 160);
      if (game.lives <= 0) {
        game.over = true;
      }
    }
  }

  // Particles
  for (const p of particles) {
    p.x += p.vx * dt;
    p.y += p.vy * dt;
    p.vx *= 0.99; p.vy *= 0.99;
    p.life -= 1000 * dt;
  }
  particles = particles.filter(p => p.life > 0);

  // Advance wave based on score
  const nextWave = 1 + Math.floor(game.score / 120);
  if (nextWave !== game.wave) {
    game.wave = nextWave;
    waveEl.classList.add('flash');
    setTimeout(() => waveEl.classList.remove('flash'), 160);
  }

  // HUD
  scoreEl.textContent = `Score: ${game.score}`;
  livesEl.textContent = `Lives: ${game.lives}`;
  waveEl.textContent = `Wave: ${game.wave}`;
}

function render(t) {
  // Background
  ctx.clearRect(0, 0, width, height);

  // Starfield
  for (const s of stars) {
    ctx.globalAlpha = s.z * 0.9;
    ctx.fillStyle = '#9abdfc';
    ctx.fillRect(s.x, s.y, s.s, s.s);
  }
  ctx.globalAlpha = 1;

  // Player
  if (!game.over) drawShip(player.x, player.y);

  // Bullets
  ctx.fillStyle = '#e5e7eb';
  for (const b of bullets) {
    ctx.fillRect(b.x - 2, b.y - 6, 4, 10);
  }

  // Enemies
  for (const e of enemies) drawEnemy(e.x, e.y, t);

  // Particles
  for (const p of particles) {
    const alpha = Math.max(0, Math.min(1, p.life / 600));
    ctx.fillStyle = p.color.replace(')', `, ${alpha})`).replace('rgb', 'rgba');
    ctx.fillRect(p.x, p.y, 2, 2);
  }

  // Game over overlay
  if (game.over) {
    ctx.save();
    ctx.fillStyle = 'rgba(5, 6, 13, 0.6)';
    ctx.fillRect(0, 0, width, height);
    ctx.fillStyle = '#cbe4ff';
    ctx.font = '24px "Press Start 2P", monospace';
    ctx.textAlign = 'center';
    ctx.fillText('GAME OVER', width / 2, height / 2 - 20);
    ctx.font = '12px "Press Start 2P", monospace';
    ctx.fillStyle = '#7aa2f7';
    ctx.fillText('Press Enter to Restart', width / 2, height / 2 + 18);
    ctx.restore();
  }
}

