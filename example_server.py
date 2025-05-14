import socket
import threading
import time
from pymavlink import mavutil

# Configuration
# serial_port = "/dev/ttyACM0"  # Change to your serial port
# baud_rate = 57600            # Change to your baud rate

tcp_host = "0.0.0.0"         # Listen on all interfaces
tcp_port = 16550             # Standard MAVLink port

# Connect to the drone via serial
# print(f"Connecting to serial port {serial_port}...")
serial_connection = mavutil.mavlink_connection(
 	"udp:127.0.0.1:14550",
    # serial_port,
    # baud=baud_rate,
    source_system=255  # Using 255 for GCS
)
print("Serial connection established")

# Set up TCP server
tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
tcp_server.bind((tcp_host, tcp_port))
tcp_server.listen(5)  # Allow up to 5 connections
print(f"TCP server listening on {tcp_host}:{tcp_port}")

# List to keep track of client connections
clients = []
clients_lock = threading.Lock()

def handle_client(client_socket, client_address):
    """Handle a client connection."""
    print(f"New client connected: {client_address}")
    
    try:
        while True:
            # Read from TCP client
            try:
                data = client_socket.recv(1024)
                if not data:
                    break  # Client disconnected
                
                # Forward from TCP client to serial
                serial_connection.write(data)
            except Exception as e:
                print(f"Error reading from client {client_address}: {e}")
                break
    finally:
        with clients_lock:
            clients.remove(client_socket)
        client_socket.close()
        print(f"Client disconnected: {client_address}")

def accept_clients():
    """Accept new client connections."""
    while True:
        try:
            client_socket, client_address = tcp_server.accept()
            with clients_lock:
                clients.append(client_socket)
            
            # Start a new thread to handle this client
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address),
                daemon=True
            )
            client_thread.start()
        except Exception as e:
            print(f"Error accepting client: {e}")
            time.sleep(1)  # Avoid CPU spinning on error

def forward_from_serial_to_tcp():
    """Read messages from serial and forward to all TCP clients."""
    while True:
        try:
            # Wait for a message from the serial connection
            msg = serial_connection.recv_match(blocking=True)
            if msg is not None:
                # Convert the message back to bytes
                msg_bytes = msg.get_msgbuf()
                
                # Send to all TCP clients
                with clients_lock:
                    disconnected_clients = []
                    for client in clients:
                        try:
                            client.send(msg_bytes)
                        except Exception:
                            # Mark client for removal
                            disconnected_clients.append(client)
                    
                    # Remove disconnected clients
                    for client in disconnected_clients:
                        clients.remove(client)
                        try:
                            client.close()
                        except:
                            pass
        except Exception as e:
            print(f"Error in serial to TCP forwarding: {e}")
            time.sleep(0.1)  # Avoid CPU spinning on error

if __name__ == "__main__":
    # Start the client acceptance thread
    accept_thread = threading.Thread(target=accept_clients, daemon=True)
    accept_thread.start()
    
    # Start the serial-to-TCP forwarding thread
    forward_thread = threading.Thread(target=forward_from_serial_to_tcp, daemon=True)
    forward_thread.start()
    
    try:
        print("Bridge is running. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        # Clean up
        tcp_server.close()
        serial_connection.close()
        with clients_lock:
            for client in clients:
                try:
                    client.close()
                except:
                    pass