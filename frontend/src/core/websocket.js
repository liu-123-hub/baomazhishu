const RECONNECT_BASE_DELAY = 1000
const RECONNECT_MAX_DELAY = 30000
const HEARTBEAT_INTERVAL = 25000
const HEARTBEAT_TIMEOUT = 10000

class WebSocketClient {
  constructor() {
    this.ws = null
    this.url = null
    this.listeners = new Map()
    this.reconnectAttempts = 0
    this.reconnectTimer = null
    this.heartbeatTimer = null
    this.heartbeatTimeoutTimer = null
    this.manualClose = false
    this.connected = false
    this.connecting = false
  }

  _getWsUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    if (host) {
      return `${protocol}//${host}/ws`
    }
    return 'ws://localhost:8000/ws'
  }

  connect() {
    if (this.connected || this.connecting) return
    this.manualClose = false
    this._connect()
  }

  _connect() {
    this.connecting = true
    this.url = this._getWsUrl()

    try {
      this.ws = new WebSocket(this.url)
    } catch (e) {
      console.error('[WS] Failed to create WebSocket:', e)
      this._scheduleReconnect()
      return
    }

    this.ws.onopen = () => {
      this.connecting = false
      this.connected = true
      this.reconnectAttempts = 0
      this._startHeartbeat()
      this._emit('connected', { url: this.url })
    }

    this.ws.onmessage = (event) => {
      this._clearHeartbeatTimeout()
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'pong') {
          return
        }
        this._emit(msg.type, msg)
        this._emit('message', msg)
      } catch (e) {
        console.warn('[WS] Failed to parse message:', e)
      }
    }

    this.ws.onerror = (event) => {
      console.warn('[WS] Connection error:', event)
    }

    this.ws.onclose = (event) => {
      this.connecting = false
      const wasConnected = this.connected
      this.connected = false
      this._stopHeartbeat()
      this._emit('disconnected', { code: event.code, reason: event.reason, wasConnected })

      if (!this.manualClose) {
        this._scheduleReconnect()
      }
    }
  }

  _scheduleReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }
    const delay = Math.min(
      RECONNECT_BASE_DELAY * Math.pow(2, this.reconnectAttempts),
      RECONNECT_MAX_DELAY
    )
    this.reconnectAttempts++
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      if (!this.manualClose && !this.connected) {
        this._connect()
      }
    }, delay)
  }

  _startHeartbeat() {
    this._stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (this.connected && this.ws?.readyState === WebSocket.OPEN) {
        try {
          this.ws.send('ping')
          this.heartbeatTimeoutTimer = setTimeout(() => {
            console.warn('[WS] Heartbeat timeout, reconnecting...')
            this.ws?.close()
          }, HEARTBEAT_TIMEOUT)
        } catch (e) {
          console.warn('[WS] Failed to send ping:', e)
        }
      }
    }, HEARTBEAT_INTERVAL)
  }

  _stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
    this._clearHeartbeatTimeout()
  }

  _clearHeartbeatTimeout() {
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer)
      this.heartbeatTimeoutTimer = null
    }
  }

  disconnect() {
    this.manualClose = true
    this._stopHeartbeat()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      try {
        this.ws.close()
      } catch (e) {
        // ignore
      }
      this.ws = null
    }
    this.connected = false
    this.connecting = false
  }

  on(type, callback) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set())
    }
    this.listeners.get(type).add(callback)
    return () => this.off(type, callback)
  }

  off(type, callback) {
    const callbacks = this.listeners.get(type)
    if (callbacks) {
      callbacks.delete(callback)
      if (callbacks.size === 0) {
        this.listeners.delete(type)
      }
    }
  }

  _emit(type, data) {
    const callbacks = this.listeners.get(type)
    if (callbacks) {
      callbacks.forEach((cb) => {
        try {
          cb(data)
        } catch (e) {
          console.error(`[WS] Listener error for "${type}":`, e)
        }
      })
    }
  }

  isConnected() {
    return this.connected
  }

  init() {
    this.connect()
  }
}

export const wsClient = new WebSocketClient()

export default wsClient
