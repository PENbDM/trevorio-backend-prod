from django.http import StreamingHttpResponse
from streaming.services.redis.subscriber import subscribe


async def stream_events(request):
    async def event_generator():
        async for message in subscribe():
            yield f'data: {message}\n\n'
            
    return StreamingHttpResponse(
        event_generator(),
        content_type="text/event-stream"
    )