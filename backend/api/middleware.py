import uuid


class SessionIDMiddleware:
    """
    Extracts or creates a session ID from the X-Session-ID header.
    This avoids CORS cookie issues between Next.js and Django.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session_id = request.headers.get('X-Session-ID', '').strip()
        if not session_id:
            session_id = str(uuid.uuid4())
        request.session_id = session_id

        response = self.get_response(request)
        response['X-Session-ID'] = session_id
        return response
