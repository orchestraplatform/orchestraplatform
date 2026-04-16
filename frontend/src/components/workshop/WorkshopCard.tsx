import React from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { ExternalLink, Trash2, CalendarClock, AlertTriangle } from 'lucide-react';
import { WorkshopInstanceResponse } from '../../api/generated';
import { formatAbsoluteTime, getTimeRemaining } from '../../utils';
import { useTerminateInstance } from '../../hooks/useInstances';
import { minutesRemaining, EXPIRY_WARN_MINUTES, EXPIRY_CRITICAL_MINUTES } from '../../hooks/useExpiryNotifications';

interface WorkshopCardProps {
  instance: WorkshopInstanceResponse;
}

export function WorkshopCard({ instance }: WorkshopCardProps) {
  const terminate = useTerminateInstance();

  const handleTerminate = async () => {
    if (window.confirm(`Terminate session "${instance.k8sName}"?`)) {
      try {
        await terminate.mutateAsync({ k8sName: instance.k8sName, namespace: instance.namespace });
      } catch (error) {
        console.error('Failed to terminate instance:', error);
        window.alert(`Failed to terminate session. Please try again.`);
      }
    }
  };

  const phaseColor = (phase: string) => {
    switch (phase) {
      case 'Ready':
      case 'Running':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'Pending':
      case 'Creating':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'Failed':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'Terminating':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      default:
        return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  };

  const isOpen = instance.phase === 'Ready' || instance.phase === 'Running';
  const minsLeft = minutesRemaining(instance.expiresAt);
  const isCritical = minsLeft <= EXPIRY_CRITICAL_MINUTES;
  const isWarning = !isCritical && minsLeft <= EXPIRY_WARN_MINUTES;

  return (
    <Card className={`flex flex-col transition-colors ${
      isCritical ? 'border-red-400 bg-red-50' :
      isWarning  ? 'border-amber-400 bg-amber-50' : ''
    }`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{instance.k8sName}</CardTitle>
          <Badge className={phaseColor(instance.phase)}>{instance.phase}</Badge>
        </div>
        <CardDescription>
          {instance.workshopName ?? 'Workshop'} · {instance.namespace}
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-grow space-y-3">
        {(instance.launchedAt || instance.expiresAt) && (
          <div className="flex items-start text-sm text-muted-foreground space-x-2">
            <CalendarClock className="h-4 w-4 mt-0.5 shrink-0" />
            <div className="space-y-0.5">
              {instance.launchedAt && (
                <div>
                  <span className="font-medium text-foreground">Started:</span>{' '}
                  {formatAbsoluteTime(instance.launchedAt)}
                </div>
              )}
              {instance.expiresAt && (
                <div className="flex items-center gap-1">
                  <span className="font-medium text-foreground">Ends:</span>{' '}
                  {formatAbsoluteTime(instance.expiresAt)}
                  <span className={`ml-1 text-xs font-medium ${isCritical ? 'text-red-600' : isWarning ? 'text-amber-600' : ''}`}>
                    ({getTimeRemaining(instance.expiresAt)})
                  </span>
                  {(isCritical || isWarning) && (
                    <AlertTriangle className={`h-3.5 w-3.5 ${isCritical ? 'text-red-500' : 'text-amber-500'}`} />
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="text-xs text-muted-foreground">
          Duration: {instance.durationRequested}
        </div>
      </CardContent>

      <CardFooter className="flex justify-between">
        <div>
          {isOpen && instance.url && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.open(instance.url!, '_blank')}
            >
              <ExternalLink className="h-4 w-4 mr-1" />
              Open
            </Button>
          )}
        </div>
        <Button
          variant="destructive"
          size="sm"
          onClick={handleTerminate}
          disabled={terminate.isPending}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  );
}
