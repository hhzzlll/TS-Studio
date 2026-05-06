
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import TrainingModel

class TrainingControlView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        try:
            job = TrainingModel.objects.get(pk=pk, user=request.user)
            action = request.data.get('action') # 'pause', 'resume', 'stop'
            
            if action == 'pause':
                if job.status == 'running':
                    job.status = 'paused'
                    job.save()
                    return Response({'status': 'Job paused'})
                else:
                    return Response({'error': f'Cannot pause job in {job.status} state'}, status=400)
            
            elif action == 'resume':
                if job.status == 'paused':
                    job.status = 'running'
                    job.save()
                    return Response({'status': 'Job resumed'})
                else:
                     return Response({'error': f'Cannot resume job in {job.status} state'}, status=400)
            
            elif action == 'stop':
                # We interpret stop as cancel
                job.status = 'cancelled'
                job.save()
                return Response({'status': 'Job cancellation requested'})
                
            else:
                return Response({'error': 'Invalid action'}, status=400)

        except TrainingModel.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
