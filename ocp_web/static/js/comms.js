// WebSocket Communication Module for OCP Web Viewer
// Simplified version without VSCode dependency

export class Comms {
    constructor(host, port) {
        this.host = host;
        this.port = port;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.messageQueue = [];
        this.isConnected = false;
        
        this.connect();
    }
    
    connect() {
        try {
            this.ws = new WebSocket(`ws://${this.host}:${this.port}/`);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                
                // Send registration message
                this.send('L:', '');
                
                // Process queued messages
                while (this.messageQueue.length > 0) {
                    const message = this.messageQueue.shift();
                    this.ws.send(message);
                }
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = event.data;
                    if (typeof data === 'string') {
                        // Convert WebSocket message to window.postMessage for compatibility
                        const message = this.parseMessage(data);
                        window.postMessage(message, '*');
                    }
                } catch (error) {
                    console.error('Error processing WebSocket message:', error);
                }
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                this.attemptReconnect();
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.isConnected = false;
            };
            
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.attemptReconnect();
        }
    }
    
    parseMessage(data) {
        // Parse message format: "TYPE:CONTENT"
        if (data.length < 2) return null;
        
        const type = data[0];
        const content = data.substring(2);
        
        try {
            const parsed = JSON.parse(content);
            return { type: this.getMessageType(type), data: parsed };
        } catch (error) {
            // For simple messages that aren't JSON
            return { type: this.getMessageType(type), text: content };
        }
    }
    
    getMessageType(typeChar) {
        const types = {
            'C': 'command',
            'D': 'data', 
            'S': 'config',
            'U': 'update',
            'L': 'listen',
            'B': 'backend',
            'R': 'response'
        };
        return types[typeChar] || 'unknown';
    }
    
    sendStatus(message) {
        this.send('U:', JSON.stringify({
            command: 'status',
            text: message
        }));
    }
    
    send(message) {
        if (this.isConnected && this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(message);
        } else {
            // Queue message for when connection is restored
            this.messageQueue.push(message);
            console.log('Message queued (not connected):', message);
        }
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectDelay * this.reconnectAttempts);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }
    
    close() {
        this.isConnected = false;
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}