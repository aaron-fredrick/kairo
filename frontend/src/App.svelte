<script>
  let rooms = [
    { id: 1, name: 'general', description: 'General discussion channel' },
    { id: 2, name: 'random', description: 'Random thoughts & links' },
    { id: 3, name: 'tech', description: 'Technology and coding talk' },
    { id: 4, name: 'announcements', description: 'Important updates' }
  ];

  let selectedRoomId = 1;
  let messages = [
    { id: 1, sender: 'swift-otter-245', content: 'Welcome to Kairo! This is a real-time messaging application.', time: '10:24 AM' },
    { id: 2, sender: 'calm-badger-892', content: 'Does it support horizontal scaling?', time: '10:25 AM' },
    { id: 3, sender: 'swift-otter-245', content: 'Yes, it uses Redis Pub/Sub to coordinate messages across multiple stateless FastAPI nodes!', time: '10:26 AM' }
  ];

  let currentMessage = '';
  let username = 'anonymous-fox-123';

  function sendMessage() {
    if (!currentMessage.trim()) return;
    messages = [
      ...messages,
      {
        id: messages.length + 1,
        sender: username,
        content: currentMessage,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ];
    currentMessage = '';
  }

  /* 
  import { onMount } from 'svelte';
  
  onMount(async () => {
    // 1. Fetching from the backend API using relative paths
    // The ngrok-skip-browser-warning header ensures ngrok's anti-abuse screen doesn't block API calls
    try {
      const response = await fetch('/api/v1/rooms', {
        headers: {
          'ngrok-skip-browser-warning': 'true'
        }
      });
      if (response.ok) {
        const data = await response.json();
        console.log("Rooms loaded from API:", data);
      }
    } catch (e) {
      console.error("Failed to fetch rooms:", e);
    }

    // 2. Connecting to WebSocket relatively
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/${selectedRoomId}`;
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      console.log("Realtime event received:", event.data);
    };
  });
  */
</script>

<main class="app-layout">
  <!-- Sidebar -->
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-icon">⚡</span>
        <h1>KAIRO</h1>
      </div>
    </div>
    
    <div class="section-title">CHANNELS</div>
    <nav class="room-list">
      {#each rooms as room}
        <button 
          class="room-item" 
          class:active={room.id === selectedRoomId}
          on:click={() => selectedRoomId = room.id}
        >
          <span class="hash">#</span>
          <span class="room-name">{room.name}</span>
        </button>
      {/each}
    </nav>

    <div class="user-profile">
      <div class="avatar">
        <span class="avatar-text">{username.slice(0, 2).toUpperCase()}</span>
        <span class="status-indicator online"></span>
      </div>
      <div class="user-info">
        <span class="username">{username}</span>
        <span class="user-role">Guest User</span>
      </div>
    </div>
  </aside>

  <!-- Chat Area -->
  <section class="chat-container">
    <header class="chat-header">
      <div class="room-title">
        <h2>#{rooms.find(r => r.id === selectedRoomId)?.name || 'general'}</h2>
        <p class="room-description">{rooms.find(r => r.id === selectedRoomId)?.description || ''}</p>
      </div>
      <div class="connection-status">
        <span class="status-dot"></span>
        Connected
      </div>
    </header>

    <div class="message-history">
      {#each messages as message}
        <div class="message-card" class:self={message.sender === username}>
          <div class="message-avatar">
            {message.sender.slice(0, 2).toUpperCase()}
          </div>
          <div class="message-content-wrapper">
            <div class="message-meta">
              <span class="message-sender">{message.sender}</span>
              <span class="message-time">{message.time}</span>
            </div>
            <p class="message-text">{message.content}</p>
            {#if message.id === 2}
              <div class="message-attachment">
                <!-- Placeholder for future thumbnail rendering -->
                <div class="image-placeholder">
                  <span class="icon">🖼️</span> architecture_diagram.png
                </div>
              </div>
            {/if}
          </div>
        </div>
      {/each}
    </div>

    <form class="message-input-form" on:submit|preventDefault={sendMessage}>
      <button type="button" class="attachment-btn" title="Upload File">
        📎
      </button>
      <input 
        type="text" 
        bind:value={currentMessage} 
        placeholder="Message #{rooms.find(r => r.id === selectedRoomId)?.name || 'general'}..." 
      />
      <button type="submit" class="send-btn" disabled={!currentMessage.trim()}>Send</button>
    </form>
  </section>
</main>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    background-color: #0b0f19;
    color: #f3f4f6;
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
  }

  .app-layout {
    display: flex;
    height: 100vh;
    width: 100vw;
    overflow: hidden;
  }

  /* Sidebar styling */
  .sidebar {
    width: 260px;
    background-color: #111827;
    border-right: 1px solid #1f2937;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
  }

  .sidebar-header {
    padding: 1.5rem;
    border-bottom: 1px solid #1f2937;
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .logo-icon {
    font-size: 1.5rem;
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
  }

  .logo h1 {
    font-size: 1.25rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    margin: 0;
    background: linear-gradient(to right, #ffffff, #9ca3af);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .section-title {
    padding: 1.5rem 1.5rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 700;
    color: #4b5563;
    letter-spacing: 0.1em;
  }

  .room-list {
    flex: 1;
    overflow-y: auto;
    padding: 0 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .room-item {
    background: transparent;
    border: none;
    outline: none;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    color: #9ca3af;
    border-radius: 8px;
    text-align: left;
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .room-item:hover {
    background-color: rgba(255, 255, 255, 0.03);
    color: #f3f4f6;
  }

  .room-item.active {
    background-color: rgba(99, 102, 241, 0.15);
    color: #818cf8;
    font-weight: 600;
  }

  .hash {
    color: #4b5563;
    font-weight: 400;
  }

  .room-item.active .hash {
    color: #818cf8;
  }

  .user-profile {
    padding: 1rem;
    background-color: #0f172a;
    border-top: 1px solid #1f2937;
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .avatar {
    position: relative;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 0.9rem;
    color: white;
  }

  .avatar-text {
    letter-spacing: 0.05em;
  }

  .status-indicator {
    position: absolute;
    bottom: 0;
    right: 0;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid #0f172a;
  }

  .status-indicator.online {
    background-color: #10b981;
  }

  .user-info {
    display: flex;
    flex-direction: column;
  }

  .username {
    font-size: 0.9rem;
    font-weight: 600;
    color: #f3f4f6;
  }

  .user-role {
    font-size: 0.75rem;
    color: #6b7280;
  }

  /* Chat Container */
  .chat-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    background-color: #0b1329;
  }

  .chat-header {
    height: 70px;
    padding: 0 1.5rem;
    border-bottom: 1px solid #1f2937;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .room-title h2 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 700;
  }

  .room-description {
    margin: 0.2rem 0 0;
    font-size: 0.8rem;
    color: #6b7280;
  }

  .connection-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: #10b981;
    font-weight: 500;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #10b981;
    box-shadow: 0 0 8px #10b981;
  }

  .message-history {
    flex: 1;
    padding: 1.5rem;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .message-card {
    display: flex;
    gap: 1rem;
    max-width: 80%;
  }

  .message-card.self {
    align-self: flex-start;
  }

  .message-avatar {
    width: 38px;
    height: 38px;
    border-radius: 8px;
    background: #1f2937;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.85rem;
    color: #9ca3af;
    flex-shrink: 0;
  }

  .message-card.self .message-avatar {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    color: white;
  }

  .message-content-wrapper {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .message-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .message-sender {
    font-size: 0.85rem;
    font-weight: 600;
    color: #e5e7eb;
  }

  .message-time {
    font-size: 0.75rem;
    color: #6b7280;
  }

  .message-text {
    margin: 0;
    font-size: 0.95rem;
    color: #d1d5db;
    line-height: 1.5;
  }

  /* Form */
  .message-input-form {
    padding: 1.5rem;
    display: flex;
    gap: 0.75rem;
    border-top: 1px solid #1f2937;
  }

  .message-input-form input {
    flex: 1;
    background-color: #111827;
    border: 1px solid #1f2937;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    color: #f3f4f6;
    font-size: 0.95rem;
    outline: none;
    transition: border-color 0.2s ease;
  }

  .message-input-form input:focus {
    border-color: #6366f1;
  }

  .attachment-btn {
    background: transparent;
    border: 1px solid #1f2937;
    color: #9ca3af;
    border-radius: 8px;
    padding: 0 1rem;
    font-size: 1.1rem;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .attachment-btn:hover {
    background: rgba(255, 255, 255, 0.05);
    color: #f3f4f6;
  }

  .message-input-form .send-btn {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    color: white;
    border: none;
    outline: none;
    border-radius: 8px;
    padding: 0 1.5rem;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s ease;
  }

  .message-input-form .send-btn:hover:not(:disabled) {
    opacity: 0.9;
  }

  .message-input-form .send-btn:disabled {
    background: #1f2937;
    color: #4b5563;
    cursor: not-allowed;
  }

  .message-attachment {
    margin-top: 0.75rem;
  }

  .image-placeholder {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background-color: #111827;
    border: 1px dashed #374151;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    font-size: 0.85rem;
    color: #9ca3af;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .image-placeholder:hover {
    border-color: #6366f1;
    color: #e5e7eb;
  }
</style>
