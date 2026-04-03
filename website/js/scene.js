/* ═══════════════════════════════════════════════════════════════
   Neurocomputer — Geeky 3D Scene
   Wireframe icosahedron + orbiting nodes + code rain
   ═══════════════════════════════════════════════════════════════ */

(function () {
    const container = document.getElementById('canvas-container');
    if (!container) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 40;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // ── Mouse tracking ──────────────────────────────────────
    let mouseX = 0, mouseY = 0;
    const halfW = window.innerWidth / 2;
    const halfH = window.innerHeight / 2;
    document.addEventListener('mousemove', e => {
        mouseX = (e.clientX - halfW) * 0.03;
        mouseY = (e.clientY - halfH) * 0.03;
    });

    // ── Color palette ───────────────────────────────────────
    const ACCENT = 0x00e5a0;   // Geeky green
    const DIM    = 0x1a3a2a;
    const PURPLE = 0x764ba2;

    // ── Central wireframe icosahedron ────────────────────────
    const icoGeo  = new THREE.IcosahedronGeometry(8, 1);
    const icoMat  = new THREE.MeshBasicMaterial({
        color: ACCENT,
        wireframe: true,
        transparent: true,
        opacity: 0.25
    });
    const ico = new THREE.Mesh(icoGeo, icoMat);
    scene.add(ico);

    // Inner glowing icosahedron (smaller, brighter)
    const icoInnerGeo = new THREE.IcosahedronGeometry(4, 0);
    const icoInnerMat = new THREE.MeshBasicMaterial({
        color: ACCENT,
        wireframe: true,
        transparent: true,
        opacity: 0.5
    });
    const icoInner = new THREE.Mesh(icoInnerGeo, icoInnerMat);
    scene.add(icoInner);

    // ── Orbiting data nodes ─────────────────────────────────
    const nodeCount = 60;
    const nodeGeo   = new THREE.SphereGeometry(0.15, 6, 6);
    const nodeMat   = new THREE.MeshBasicMaterial({
        color: ACCENT,
        transparent: true,
        opacity: 0.7
    });
    const nodes     = [];
    const orbits    = [];

    for (let i = 0; i < nodeCount; i++) {
        const mesh   = new THREE.Mesh(nodeGeo, nodeMat.clone());
        const radius = 12 + Math.random() * 18;
        const speed  = (0.001 + Math.random() * 0.003) * (Math.random() > 0.5 ? 1 : -1);
        const tilt   = Math.random() * Math.PI;
        const phase  = Math.random() * Math.PI * 2;

        nodes.push(mesh);
        orbits.push({ radius, speed, tilt, phase, angle: phase });
        scene.add(mesh);
    }

    // Lines connecting nearby nodes
    const lineMat = new THREE.LineBasicMaterial({
        color: ACCENT,
        transparent: true,
        opacity: 0.08,
        blending: THREE.AdditiveBlending
    });

    let lineSegments = null;
    function updateLines() {
        if (lineSegments) scene.remove(lineSegments);
        const positions = [];
        const maxDist = 14;
        for (let i = 0; i < nodes.length; i++) {
            for (let j = i + 1; j < nodes.length; j++) {
                const d = nodes[i].position.distanceTo(nodes[j].position);
                if (d < maxDist) {
                    positions.push(
                        nodes[i].position.x, nodes[i].position.y, nodes[i].position.z,
                        nodes[j].position.x, nodes[j].position.y, nodes[j].position.z
                    );
                }
            }
        }
        const lineGeo = new THREE.BufferGeometry();
        lineGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        lineSegments = new THREE.LineSegments(lineGeo, lineMat);
        scene.add(lineSegments);
    }

    // ── Code rain particles ─────────────────────────────────
    // We simulate vertical "rain" columns using a simple particle system
    const isMobile = window.innerWidth < 768;
    const rainCount = isMobile ? 300 : 800;
    const rainGeo   = new THREE.BufferGeometry();
    const rainPos   = new Float32Array(rainCount * 3);
    const rainVel   = [];

    for (let i = 0; i < rainCount; i++) {
        rainPos[i * 3]     = (Math.random() - 0.5) * 120;   // x: spread wide
        rainPos[i * 3 + 1] = (Math.random() - 0.5) * 80;    // y: vertical
        rainPos[i * 3 + 2] = (Math.random() - 0.5) * 60;    // z: depth
        rainVel.push(0.02 + Math.random() * 0.06);           // fall speed
    }

    rainGeo.setAttribute('position', new THREE.Float32BufferAttribute(rainPos, 3));
    const rainMat = new THREE.PointsMaterial({
        color: ACCENT,
        size: isMobile ? 0.12 : 0.08,
        transparent: true,
        opacity: 0.25,
        blending: THREE.AdditiveBlending
    });
    const rain = new THREE.Points(rainGeo, rainMat);
    scene.add(rain);

    // ── Accent ring ─────────────────────────────────────────
    const ringGeo = new THREE.TorusGeometry(16, 0.05, 8, 100);
    const ringMat = new THREE.MeshBasicMaterial({
        color: PURPLE,
        transparent: true,
        opacity: 0.15
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = Math.PI / 2;
    scene.add(ring);

    // Second ring at different angle
    const ring2 = new THREE.Mesh(
        new THREE.TorusGeometry(22, 0.03, 8, 100),
        new THREE.MeshBasicMaterial({ color: DIM, transparent: true, opacity: 0.1 })
    );
    ring2.rotation.x = Math.PI / 3;
    ring2.rotation.y = Math.PI / 6;
    scene.add(ring2);

    // ── Animation loop ──────────────────────────────────────
    let frame = 0;
    function animate() {
        requestAnimationFrame(animate);
        frame++;

        // Smooth mouse follow
        camera.position.x += (mouseX - camera.position.x) * 0.02;
        camera.position.y += (-mouseY - camera.position.y) * 0.02;
        camera.lookAt(scene.position);

        // Rotate wireframes
        ico.rotation.x += 0.002;
        ico.rotation.y += 0.003;
        icoInner.rotation.x -= 0.004;
        icoInner.rotation.z += 0.003;

        // Rotate rings
        ring.rotation.z += 0.001;
        ring2.rotation.z -= 0.0007;

        // Update orbiting nodes
        for (let i = 0; i < nodes.length; i++) {
            const o = orbits[i];
            o.angle += o.speed;
            nodes[i].position.x = o.radius * Math.cos(o.angle) * Math.cos(o.tilt);
            nodes[i].position.y = o.radius * Math.sin(o.angle);
            nodes[i].position.z = o.radius * Math.cos(o.angle) * Math.sin(o.tilt);
        }

        // Update connecting lines every 3 frames
        if (frame % 3 === 0) updateLines();

        // Code rain: fall downward, wrap around
        const rp = rainGeo.attributes.position.array;
        for (let i = 0; i < rainCount; i++) {
            rp[i * 3 + 1] -= rainVel[i];
            if (rp[i * 3 + 1] < -40) {
                rp[i * 3 + 1] = 40;
            }
        }
        rainGeo.attributes.position.needsUpdate = true;

        renderer.render(scene, camera);
    }
    animate();

    // ── Resize ──────────────────────────────────────────────
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
})();
