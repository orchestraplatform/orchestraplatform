import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { ExternalLink, Trash2, CalendarClock, AlertTriangle, PlusCircle } from 'lucide-react';
import { WorkshopInstanceResponse } from '../../api/generated';
import { formatAbsoluteTime, getTimeRemaining } from '../../utils';
import { useTerminateInstance, useExtendInstance } from '../../hooks/useInstances';
import { minutesRemaining, EXPIRY_WARN_MINUTES, EXPIRY_CRITICAL_MINUTES } from '../../hooks/useExpiryNotifications';
import { useToast } from '../ui/Toast';
import { useTick } from '../../contexts/TickContext';

interface WorkshopCardProps {
  instance: WorkshopInstanceResponse;
}

export function WorkshopCard({ instance }: WorkshopCardProps) {
  const terminate = useTerminateInstance();
  const extend = useExtendInstance();
  const { addToast } = useToast();
  const [confirmOpen, setConfirmOpen] = useState(false);

  const handleTerminate = () => setConfirmOpen(true);

  const handleConfirmTerminate = async () => {
    setConfirmOpen(false);
    try {
      await terminate.mutateAsync({ k8sName: instance.k8sName, namespace: instance.namespace });
    } catch {
      addToast({ type: 'error', message: 'Failed to terminate session. Please try again.' });
    }
  };

  const handleExtend = async () => {
    try {
      await extend.mutateAsync({ k8sName: instance.k8sName, namespace: instance.namespace });
      addToast({ type: 'success', message: 'Session extended by 1 hour.' });
    } catch {
      addToast({ type: 'error', message: 'Failed to extend session.' });
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

  useTick();

  const isOpen = instance.phase === 'Ready' || instance.phase === 'Running';
  const minsLeft = minutesRemaining(instance.expiresAt);
  const isCritical = minsLeft <= EXPIRY_CRITICAL_MINUTES;
  const isWarning = !isCritical && minsLeft <= EXPIRY_WARN_MINUTES;

  return (
    <>
    <ConfirmDialog
      isOpen={confirmOpen}
      title="Terminate session?"
      message={`This will permanently end session "${instance.k8sName}". Any unsaved work will be lost.`}
      confirmLabel="Terminate"
      onConfirm={handleConfirmTerminate}
      onCancel={() => setConfirmOpen(false)}
    />
    <Card className="flex flex-col transition-colors">
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
                <div className="flex items-center gap-1 flex-wrap">
                  <span className="font-medium text-foreground">Ends:</span>{' '}
                  {formatAbsoluteTime(instance.expiresAt)}
                  {(isCritical || isWarning) && (
                    <span className={`ml-1 inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] font-bold
                      ${isCritical
                        ? 'border-red-200 bg-red-50 text-red-700'
                        : 'border-amber-200 bg-amber-50 text-amber-700'}`}>
                      <AlertTriangle className="h-2.5 w-2.5" />
                      {getTimeRemaining(instance.expiresAt)} left
                    </span>
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
        <div className="flex items-center gap-2">
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
          {isOpen && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleExtend}
              disabled={extend.isPending}
              className="text-indigo-600 border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"
            >
              <PlusCircle className="h-4 w-4 mr-1" />
              +1h
            </Button>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleTerminate}
          disabled={terminate.isPending}
          className="text-destructive hover:bg-destructive/10 hover:text-destructive"
        >
          <Trash2 className="h-4 w-4 mr-1" />
          Terminate
        </Button>
      </CardFooter>
    </Card>
    </>
  );
}
