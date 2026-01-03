import { ref } from 'vue';

export interface WebSocketMessage {
  type: string;
  data: any;
}

export class WebSocketService {
  private static instance: WebSocketService;
  private socket: WebSocket | null = null;
  private connectionStatus: boolean = false;
  private eventListeners: Map<string, Array<(data: any) => void>> = new Map();
  private reconnectAttempts: number = 0;
  private reconnectDelay: number = 1000;
  private maxReconnectAttempts: number = 5;
  private reconnectTimer: number | null = null;

  static getInstance(): WebSocketService {
    if (!WebSocketService.instance) {
      WebSocketService.instance = new WebSocketService();
    }
    return WebSocketService.instance;
  }

  connect(url: string): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      this.socket = new WebSocket(url);
      
      this.socket.onopen = () => {
        console.log('WebSocket connected');
        this.connectionStatus = true;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
      };

      this.socket.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.socket.onclose = () => {
        console.log('WebSocket disconnected');
        this.connectionStatus = false;
        this.attemptReconnect(url);
      };

      this.socket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.attemptReconnect(url);
    }
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    
    this.connectionStatus = false;
  }

  send(message: WebSocketMessage): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }

  on(eventType: string, callback: (data: any) => void): void {
    if (!this.eventListeners.has(eventType)) {
      this.eventListeners.set(eventType, []);
    }
    
    this.eventListeners.get(eventType)?.push(callback);
  }

  off(eventType: string, callback: (data: any) => void): void {
    const listeners = this.eventListeners.get(eventType);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  isConnected(): boolean {
    return this.connectionStatus;
  }

  private handleMessage(message: WebSocketMessage): void {
    const listeners = this.eventListeners.get(message.type);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(message.data);
        } catch (error) {
          console.error(`Error in WebSocket event listener for ${message.type}:`, error);
        }
      });
    }
  }

  private attemptReconnect(url: string): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

    this.reconnectTimer = window.setTimeout(() => {
      this.connect(url);
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 10000); // Exponential backoff
    }, this.reconnectDelay);
  }
}