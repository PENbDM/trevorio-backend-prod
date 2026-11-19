from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from tracking.services.redis.record_db_table_user import make_record

class TrackingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # print("========== INCOMING REQUEST ==========")
        # print("Method:", request.method)
        # print("Payload:", request.data)
        # print("Datasource ID:", request.data.get("datasource_id"))
        # print("Table ID:", request.data.get("table_id"))
        # print("User ID:", request.user.id)
        # print("======================================")
        make_record(request.user.id,request.data.get("table_id"),request.data.get("datasource_id"))
        return Response({
            "status": "ok",
            "received": request.data
        })