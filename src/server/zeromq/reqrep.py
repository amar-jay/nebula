import zmq

class RequestReplyServer:
    def __init__(self, host='localhost', port=5555):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f'tcp://{host}:{port}')
        print(f'Server listening on tcp://{host}:{port}')

    def run(self):
        while True:
            message = self.socket.recv_string()
            print(f'Received request: {message}')
            # Process the request and send a response
            response = self.process_request(message)
            self.socket.send_string(response)

    def process_request(self, message):
        # Implement your request processing logic here
        return f'Processed: {message}'


class RequestReplyClient:
    def __init__(self, host='localhost', port=5555):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f'tcp://{host}:{port}')

    def send_request(self, message):
        self.socket.send_string(message)
        response = self.socket.recv_string()
        print(f'Received response: {response}')
        return response


if __name__ == '__main__':
    # Example usage
    server = RequestReplyServer()
    # To run the server, uncomment the line below
    # server.run()

    client = RequestReplyClient()
    client.send_request('Hello, Drone!')