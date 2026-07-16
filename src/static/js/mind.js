/**
 * The Living Mind – Experimental UI for Jarvis OS
 * Main orchestrator.
 */

// ---- Dependencies ----
// Cytoscape is loaded globally via CDN.

// ---- Graph data (nodes & edges) ----
const NODES = [
    { id: 'user', label: 'User', type: 'user', color: '#6a8cff' },
    { id: 'conversation', label: 'Conversation', type: 'conversation', color: '#8899cc' },
    { id: 'intent', label: 'Intent', type: 'executive', color: '#4a8fc7' },
    { id: 'goals', label: 'Goals', type: 'executive', color: '#4a8fc7' },
    { id: 'strategy', label: 'Strategy', type: 'executive', color: '#4a8fc7' },
    { id: 'planner', label: 'Planner', type: 'executive', color: '#4a8fc7' },
    { id: 'decision', label: 'Decision Engine', type: 'executive', color: '#4a8fc7' },
    { id: 'delegation', label: 'Delegation', type: 'executive', color: '#4a8fc7' },
    { id: 'execution', label: 'Execution', type: 'execution', color: '#4CAF50' },
    { id: 'reflection', label: 'Reflection', type: 'cognitive', color: '#9C27B0' },
    { id: 'learning', label: 'Learning', type: 'cognitive', color: '#9C27B0' },
    { id: 'knowledge', label: 'Knowledge', type: 'cognitive', color: '#9C27B0' },
    { id: 'workspace', label: 'Workspace', type: 'cognitive', color: '#9C27B0' },
    { id: 'memory', label: 'Memory', type: 'cognitive', color: '#9C27B0' },
    { id: 'capability_platform', label: 'Capability Platform', type: 'capability', color: '#FF9800' },
    { id: 'capability_resolver', label: 'Capability Resolver', type: 'capability', color: '#FF9800' },
    { id: 'capability_registry', label: 'Capability Registry', type: 'capability', color: '#FF9800' },
    { id: 'scheduler', label: 'Scheduler', type: 'execution', color: '#4CAF50' },
    { id: 'event_bus', label: 'Event Bus', type: 'infrastructure', color: '#78909C' },
    { id: 'system', label: 'System', type: 'infrastructure', color: '#78909C' },
];

const EDGES = [
    { source: 'user', target: 'conversation' },
    { source: 'conversation', target: 'intent' },
    { source: 'intent', target: 'goals' },
    { source: 'goals', target: 'strategy' },
    { source: 'strategy', target: 'planner' },
    { source: 'planner', target: 'decision' },
    { source: 'decision', target: 'delegation' },
    { source: 'delegation', target: 'execution' },
    { source: 'execution', target: 'capability_platform' },
    { source: 'capability_platform', target: 'capability_resolver' },
    { source: 'capability_resolver', target: 'capability_registry' },
    { source: 'capability_platform', target: 'scheduler' },
    { source: 'scheduler', target: 'execution' },
    { source: 'execution', target: 'reflection' },
    { source: 'reflection', target: 'learning' },
    { source: 'learning', target: 'knowledge' },
    { source: 'knowledge', target: 'workspace' },
    { source: 'workspace', target: 'memory' },
    { source: 'memory', target: 'goals' },
    { source: 'event_bus', target: 'execution' },
    { source: 'event_bus', target: 'delegation' },
    { source: 'system', target: 'event_bus' },
    { source: 'system', target: 'capability_registry' },
];

// ---- Cytoscape Graph Initialization ----
const graphContainer = document.getElementById('mind-graph');

const cy = cytoscape({
    container: graphContainer,
    elements: [
        ...NODES.map(n => ({ data: { id: n.id, label: n.label, type: n.type, color: n.color } })),
        ...EDGES.map(e => ({ data: { source: e.source, target: e.target } })),
    ],
    style: [
        {
            selector: 'node',
            style: {
                'background-color': 'data(color)',
                'width': 48,
                'height': 48,
                'border-width': 2,
                'border-color': 'rgba(255,255,255,0.15)',
                'label': 'data(label)',
                'font-size': '10px',
                'color': '#b0c8e8',
                'text-valign': 'bottom',
                'text-halign': 'center',
                'text-margin-y': 10,
                'text-max-width': 80,
                'text-wrap': 'wrap',
                'text-justification': 'center',
            },
        },
        {
            selector: 'edge',
            style: {
                'width': 1.5,
                'line-color': 'rgba(120,160,255,0.2)',
                'curve-style': 'bezier',
                'target-arrow-shape': 'none',
                'opacity': 0.6,
            },
        },
        {
            selector: 'node.user',
            style: {
                'background-color': '#6a8cff',
                'border-color': '#6a8cff',
                'width': 56,
                'height': 56,
                'font-size': '12px',
            },
        },
        {
            selector: 'node.executive',
            style: {
                'background-color': '#4a8fc7',
            },
        },
        {
            selector: 'node.cognitive',
            style: {
                'background-color': '#9C27B0',
            },
        },
        {
            selector: 'node.capability',
            style: {
                'background-color': '#FF9800',
            },
        },
        {
            selector: 'node.execution',
            style: {
                'background-color': '#4CAF50',
            },
        },
        {
            selector: 'node.infrastructure',
            style: {
                'background-color': '#78909C',
            },
        },
    ],
    layout: {
        name: 'cose',                // <-- built-in layout (no extension needed)
        idealEdgeLength: 80,
        nodeRepulsion: 600,
        gravity: 0.2,
        numIter: 1000,
        animate: false,
    },
    zoom: 0.7,
    pan: { x: 0, y: -20 },
    minZoom: 0.4,
    maxZoom: 1.4,
});

// ---- Node State Management ----
const nodeStates = {};

function setNodeState(nodeId, state, duration = 1500) {
    const node = cy.getElementById(nodeId);
    if (!node.length) return;

    const colors = {
        idle: '#4a8fc7',
        thinking: '#ffffff',
        planning: '#FFD700',
        learning: '#9C27B0',
        executing: '#4CAF50',
        warning: '#FFA726',
        failure: '#EF5350',
        sleeping: '#80DEEA',
    };

    const bg = colors[state] || colors.idle;
    node.style('background-color', bg);
    if (state === 'thinking') {
        node.style('border-color', '#ffffff');
        node.style('border-width', 4);
        node.addClass('pulse');
        setTimeout(() => node.removeClass('pulse'), duration);
    } else {
        node.style('border-color', 'rgba(255,255,255,0.15)');
        node.style('border-width', 2);
        node.removeClass('pulse');
    }

    nodeStates[nodeId] = { state, timestamp: Date.now() };
}

// ---- Thinking Pulse Animation ----
async function animateThinking() {
    const path = ['user', 'conversation', 'intent', 'goals', 'strategy', 'planner', 'decision', 'delegation', 'execution', 'capability_platform', 'capability_resolver', 'capability_registry', 'execution', 'reflection', 'learning', 'knowledge', 'workspace', 'memory'];

    // Reset all nodes to idle first
    NODES.forEach(n => setNodeState(n.id, 'idle'));

    for (const id of path) {
        setNodeState(id, 'thinking', 600);
        await sleep(300);
    }

    // Fade out
    for (const id of path) {
        setNodeState(id, 'idle', 400);
        await sleep(100);
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ---- Memory Scan Animation ----
async function animateMemoryScan() {
    // Random nodes glow
    const nodes = NODES.map(n => n.id);
    const shuffled = nodes.sort(() => Math.random() - 0.5);
    const selected = shuffled.slice(0, 5);

    for (const id of selected) {
        setNodeState(id, 'thinking', 800);
    }

    await sleep(1200);

    // Highlight the path to memory
    const path = ['user', 'conversation', 'memory'];
    for (const id of path) {
        setNodeState(id, 'learning', 600);
        await sleep(200);
    }

    await sleep(1000);
    // Reset
    NODES.forEach(n => setNodeState(n.id, 'idle'));
}

// ---- Capability Execution Animation ----
async function animateCapabilityExecution(capability = 'capability_platform') {
    const path = ['capability_platform', 'capability_resolver', 'capability_registry', 'execution'];

    for (const id of path) {
        setNodeState(id, 'executing', 600);
        await sleep(200);
    }

    await sleep(800);
    NODES.forEach(n => setNodeState(n.id, 'idle'));
}

// ---- Reflection Animation ----
async function animateReflection() {
    const cluster = ['reflection', 'learning', 'knowledge', 'workspace', 'memory'];
    for (const id of cluster) {
        setNodeState(id, 'learning', 1200);
    }
    await sleep(1500);
    NODES.forEach(n => setNodeState(n.id, 'idle'));
}

// ---- Sleep Mode Toggle ----
let sleepMode = false;

function toggleSleep() {
    sleepMode = !sleepMode;
    const overlay = document.getElementById('sleep-overlay');
    if (sleepMode) {
        overlay.classList.add('active');
        // Change colors to cyan/slow
        NODES.forEach(n => {
            const node = cy.getElementById(n.id);
            if (node.length) {
                node.style('background-color', '#80DEEA');
                node.style('opacity', 0.7);
            }
        });
    } else {
        overlay.classList.remove('active');
        // Restore colors
        NODES.forEach(n => {
            const node = cy.getElementById(n.id);
            if (node.length) {
                node.style('background-color', n.color);
                node.style('opacity', 1);
            }
        });
    }
}

// ---- Node Click: Show Info Panel ----
const infoPanel = document.getElementById('info-panel');
const infoTitle = document.getElementById('info-title');
const infoContent = document.getElementById('info-content');
const infoClose = document.getElementById('info-close');

cy.on('tap', 'node', (evt) => {
    const node = evt.target;
    const id = node.id();
    const data = node.data();
    const label = data.label || id;

    infoTitle.textContent = label;
    infoContent.innerHTML = `
        <div class="label">ID</div>
        <div class="value">${id}</div>
        <div class="label">Type</div>
        <div class="value">${data.type || 'unknown'}</div>
        <div class="label">State</div>
        <div class="value">${nodeStates[id]?.state || 'idle'}</div>
        <div class="label">Connections</div>
        <div class="value">${cy.edges(`[source="${id}"], [target="${id}"]`).length}</div>
        <div class="label">Description</div>
        <div class="value">${getNodeDescription(id)}</div>
    `;
    infoPanel.classList.remove('hidden');
});

infoClose.addEventListener('click', () => {
    infoPanel.classList.add('hidden');
});

function getNodeDescription(id) {
    const desc = {
        user: 'The human operator. The source of all interactions.',
        conversation: 'The current dialogue between Jarvis and the user.',
        intent: 'Interpretation of the user\'s goal and urgency.',
        goals: 'Active objectives. Each goal has a budget and priority.',
        strategy: 'High‑level plan to achieve the goals.',
        planner: 'Breaks goals into executable tasks.',
        decision: 'Commits to a specific course of action.',
        delegation: 'Directs tasks to capabilities and execution.',
        execution: 'Runs tasks, handles retries, monitors progress.',
        reflection: 'Reviews outcomes and identifies lessons.',
        learning: 'Integrates new knowledge and patterns.',
        knowledge: 'Stores facts, procedures, preferences, relationships.',
        workspace: 'Current mental state of Jarvis.',
        memory: 'Long‑term storage with semantic search.',
        capability_platform: 'Abstraction over all capabilities.',
        capability_resolver: 'Selects the best capability for a task.',
        capability_registry: 'Stores manifests and health of capabilities.',
        scheduler: 'Coordinates task timing and resource allocation.',
        event_bus: 'Central communication bus for all components.',
        system: 'The underlying operating system and infrastructure.',
    };
    return desc[id] || 'No description available.';
}

// ---- Notification System ----
function addNotification(message, type = 'info') {
    const container = document.getElementById('notification-container');
    const badge = document.createElement('div');
    badge.className = 'notification-badge';
    badge.textContent = message;
    container.appendChild(badge);
    setTimeout(() => {
        badge.remove();
    }, 5000);
}

// ---- Conversation ----
const messagesContainer = document.getElementById('conversation-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

function addMessage(text, sender) {
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    div.textContent = text;
    messagesContainer.appendChild(div);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function handleSend() {
    const text = userInput.value.trim();
    if (!text) return;
    userInput.value = '';
    addMessage(text, 'user');
    // Simulate thinking animation
    await animateThinking();
    // Simulate response
    const responses = [
        'I\'ve considered that. Let me refine the approach.',
        'Interesting. I\'m cross‑referencing with past experiences.',
        'I\'ll need to consult the knowledge base. One moment.',
        'I\'ve found a relevant pattern. Let me explain.',
        'That requires a multi‑step plan. I\'ll delegate accordingly.',
        'I\'ve updated the workspace. Here\'s my reasoning.',
    ];
    const reply = responses[Math.floor(Math.random() * responses.length)];
    addMessage(reply, 'assistant');
    // Trigger a notification
    addNotification('Jarvis has completed your request.', 'info');
}

sendBtn.addEventListener('click', handleSend);
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleSend();
});

// ---- Controls ----
const sleepBtn = document.createElement('button');
sleepBtn.textContent = '💤 Sleep';
sleepBtn.id = 'sleep-toggle';
sleepBtn.addEventListener('click', toggleSleep);
document.getElementById('controls')?.appendChild(sleepBtn);

// Add control buttons (Memory Scan, Capability Exec, Reflection)
const memoryBtn = document.createElement('button');
memoryBtn.textContent = '🧠 Scan Memory';
memoryBtn.addEventListener('click', animateMemoryScan);
document.getElementById('controls')?.appendChild(memoryBtn);

const capBtn = document.createElement('button');
capBtn.textContent = '⚡ Run Capability';
capBtn.addEventListener('click', () => animateCapabilityExecution());
document.getElementById('controls')?.appendChild(capBtn);

const reflectBtn = document.createElement('button');
reflectBtn.textContent = '🔄 Reflect';
reflectBtn.addEventListener('click', animateReflection);
document.getElementById('controls')?.appendChild(reflectBtn);

// ---- Live Drift Animation (nodes slowly move) ----
let driftInterval = setInterval(() => {
    cy.nodes().forEach(node => {
        const dx = (Math.random() - 0.5) * 2;
        const dy = (Math.random() - 0.5) * 2;
        node.position({
            x: node.position('x') + dx,
            y: node.position('y') + dy,
        });
    });
}, 5000);

// ---- Warmup ----
// Start with a nice idle state: a few nodes glow gently
setTimeout(() => {
    ['executive', 'cognitive', 'capability_platform', 'memory'].forEach(id => {
        setNodeState(id, 'idle');
    });
}, 500);

// ---- Simulate periodic thinking (background) ----
setInterval(async () => {
    if (!sleepMode) {
        // Randomly trigger a small animation
        const r = Math.random();
        if (r < 0.2) {
            await animateThinking();
        } else if (r < 0.35) {
            await animateMemoryScan();
        } else if (r < 0.5) {
            await animateReflection();
        }
        // add a notification occasionally
        if (Math.random() < 0.1) {
            addNotification('Jarvis is processing background tasks.', 'info');
        }
    }
}, 30000);

console.log('🧠 The Living Mind UI initialized.');
