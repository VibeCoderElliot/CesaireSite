class SecurityHeaders:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST' and request.user.is_authenticated:
            from .services import rate_limit
            if not rate_limit(f'write-user:{request.user.pk}',limit=120,seconds=60):
                from django.http import HttpResponse
                return HttpResponse('Trop de demandes. Réessayez dans une minute.',status=429)
        response = self.get_response(request)
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        if not request.path.startswith('/static/'):
            response['Cache-Control'] = 'no-store'
        return response
