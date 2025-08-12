import * as THREE from 'https://unpkg.com/three@0.159.0/build/three.module.js';
import { OrbitControls } from 'https://unpkg.com/three@0.159.0/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'https://unpkg.com/three@0.159.0/examples/jsm/loaders/GLTFLoader.js';
import { RGBELoader } from 'https://unpkg.com/three@0.159.0/examples/jsm/loaders/RGBELoader.js';
import { OBJLoader } from 'https://unpkg.com/three@0.159.0/examples/jsm/loaders/OBJLoader.js';
import { FBXLoader } from 'https://unpkg.com/three@0.159.0/examples/jsm/loaders/FBXLoader.js';
import { DRACOLoader } from 'https://unpkg.com/three@0.159.0/examples/jsm/loaders/DRACOLoader.js';
import { EffectComposer } from 'https://unpkg.com/three@0.159.0/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'https://unpkg.com/three@0.159.0/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'https://unpkg.com/three@0.159.0/examples/jsm/postprocessing/UnrealBloomPass.js';
import { FontLoader } from 'https://unpkg.com/three@0.159.0/examples/jsm/loaders/FontLoader.js';
import { TextGeometry } from 'https://unpkg.com/three@0.159.0/examples/jsm/geometries/TextGeometry.js';

const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;

const scene = new THREE.Scene();
scene.background = null;

const camera = new THREE.PerspectiveCamera(60, innerWidth / innerHeight, 0.1, 2000);
camera.position.set(4, 2.2, 6);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(0, 1, 0);

// Lights
const ambient = new THREE.AmbientLight(0xaac7ff, 0.7);
scene.add(ambient);
const dir = new THREE.DirectionalLight(0xffffff, 1.2);
dir.position.set(5, 6, 8);
dir.castShadow = true;
scene.add(dir);

// Ground grid with subtle fade
const grid = new THREE.GridHelper(60, 60, 0x1f4fff, 0x1f4fff);
grid.material.opacity = 0.12;
grid.material.transparent = true;
grid.position.y = -0.001;
scene.add(grid);

// Starfield
function makeStars() {
  const g = new THREE.BufferGeometry();
  const count = 2000;
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const r = 80 * Math.random() + 40;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    positions[i * 3 + 0] = r * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    positions[i * 3 + 2] = r * Math.cos(phi);
  }
  g.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  const m = new THREE.PointsMaterial({ size: 0.06, color: 0x9abdfc });
  const stars = new THREE.Points(g, m);
  return stars;
}
scene.add(makeStars());

// Hero objects: torus + cubes ring
const heroGroup = new THREE.Group();
const torus = new THREE.Mesh(
  new THREE.TorusKnotGeometry(0.7, 0.26, 220, 26),
  new THREE.MeshStandardMaterial({ metalness: 0.6, roughness: 0.2, color: 0x80b2ff, emissive: 0x0b1f49, emissiveIntensity: 0.4 })
);
torus.castShadow = torus.receiveShadow = true;
heroGroup.add(torus);

const ring = new THREE.Group();
for (let i = 0; i < 20; i++) {
  const cube = new THREE.Mesh(
    new THREE.BoxGeometry(0.2, 0.2, 0.2),
    new THREE.MeshStandardMaterial({ color: 0x99c1ff, metalness: 0.4, roughness: 0.3 })
  );
  const a = (i / 20) * Math.PI * 2;
  cube.position.set(Math.cos(a) * 2.2, 0.25 * Math.sin(i), Math.sin(a) * 2.2);
  cube.castShadow = cube.receiveShadow = true;
  ring.add(cube);
}
heroGroup.add(ring);
scene.add(heroGroup);

// 3D Text
const fontLoader = new FontLoader();
fontLoader.load('https://rawcdn.githack.com/mrdoob/three.js/r159/examples/fonts/Inter_Bold.json', (font) => {
  const textGeo = new TextGeometry('AIDAN TRAN', {
    font,
    size: 0.5,
    height: 0.16,
    curveSegments: 8,
    bevelEnabled: true,
    bevelThickness: 0.02,
    bevelSize: 0.02,
    bevelSegments: 3,
  });
  textGeo.center();
  const textMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.3, roughness: 0.3, emissive: 0x0a244d, emissiveIntensity: 0.35 });
  const text = new THREE.Mesh(textGeo, textMat);
  text.position.set(0, 1.4, 0);
  text.castShadow = text.receiveShadow = true;
  scene.add(text);
});

// Environment
new RGBELoader()
  .setPath('https://rawcdn.githack.com/gkjohnson/threejs-sandbox/2e2b5f69c8b0513c1f9b3e9b4efd050f8b1e69d0/hdri/')
  .load('venice_sunset_1k.hdr', (hdr) => {
    hdr.mapping = THREE.EquirectangularReflectionMapping;
    scene.environment = hdr;
  });

// Postprocessing
const composer = new EffectComposer(renderer);
const renderPass = new RenderPass(scene, camera);
composer.addPass(renderPass);
const bloomPass = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.8, 0.8, 0.85);
composer.addPass(bloomPass);

// Loaders
const draco = new DRACOLoader();
draco.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.6/');
const gltf = new GLTFLoader();
gltf.setDRACOLoader(draco);
const obj = new OBJLoader();
const fbx = new FBXLoader();

const dropZone = document.body;
function onFiles(files) {
  if (!files || !files.length) return;
  const file = files[0];
  const url = URL.createObjectURL(file);
  loadModel(url, file.name.toLowerCase());
}

dropZone.addEventListener('dragover', (e) => { e.preventDefault(); });
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  onFiles(e.dataTransfer.files);
});

document.getElementById('file').addEventListener('change', (e) => onFiles(e.target.files));

let currentModel = null;
function clearModel() {
  if (currentModel) {
    scene.remove(currentModel);
    currentModel.traverse?.((c) => {
      if (c.geometry) c.geometry.dispose();
      if (c.material) {
        if (Array.isArray(c.material)) c.material.forEach((m) => m.dispose());
        else c.material.dispose();
      }
    });
    currentModel = null;
  }
}

function focusOn(object3d) {
  const box = new THREE.Box3().setFromObject(object3d);
  const size = new THREE.Vector3();
  const center = new THREE.Vector3();
  box.getSize(size);
  box.getCenter(center);
  const maxDim = Math.max(size.x, size.y, size.z);
  const fov = camera.fov * (Math.PI / 180);
  let cameraZ = Math.abs(maxDim / Math.tan(fov / 2));
  cameraZ *= 1.4;
  camera.position.set(center.x + cameraZ * 0.4, center.y + cameraZ * 0.25, center.z + cameraZ);
  controls.target.copy(center);
  controls.update();
}

async function loadModel(url, name) {
  clearModel();
  try {
    let root;
    if (name.endsWith('.glb') || name.endsWith('.gltf')) {
      const res = await gltf.loadAsync(url);
      root = res.scene;
    } else if (name.endsWith('.obj')) {
      root = await obj.loadAsync(url);
    } else if (name.endsWith('.fbx')) {
      root = await fbx.loadAsync(url);
    } else {
      alert('Unsupported format. Use .glb/.gltf/.obj/.fbx');
      return;
    }
    root.traverse((c) => { if (c.isMesh) { c.castShadow = c.receiveShadow = true; c.material.side = THREE.FrontSide; } });
    currentModel = root;
    scene.add(root);
    focusOn(root);
  } catch (e) {
    console.error(e);
    alert('Failed to load model');
  }
}

// UI buttons
document.getElementById('reset').addEventListener('click', () => {
  camera.position.set(4, 2.2, 6);
  controls.target.set(0, 1, 0);
  controls.update();
});

let wireframeEnabled = false;
document.getElementById('wire').addEventListener('click', () => {
  wireframeEnabled = !wireframeEnabled;
  const apply = (obj) => {
    obj.traverse?.((c) => {
      if (c.isMesh && c.material) {
        if (Array.isArray(c.material)) c.material.forEach((m) => (m.wireframe = wireframeEnabled));
        else c.material.wireframe = wireframeEnabled;
      }
    });
  };
  if (currentModel) apply(currentModel);
  apply(heroGroup);
});

let bloomEnabled = true;
document.getElementById('bloom').addEventListener('click', () => {
  bloomEnabled = !bloomEnabled;
  bloomPass.enabled = bloomEnabled;
});

// Animate
let t = 0;
function animate() {
  requestAnimationFrame(animate);
  t += 0.016;
  torus.rotation.x += 0.005;
  torus.rotation.y += 0.008;
  ring.rotation.y -= 0.003;
  ring.children.forEach((c, i) => {
    c.position.y = 0.35 * Math.sin(t * 1.6 + i * 0.6);
  });
  controls.update();
  composer.render();
}
animate();

// Resize
addEventListener('resize', () => {
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(innerWidth, innerHeight);
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  composer.setSize(innerWidth, innerHeight);
});

