import React from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { ExternalLink, Trash2, Clock, Server } from 'lucide-react';
import { Workshop } from '../../types';
import { formatDuration, getTimeRemaining } from '../../utils';
import { useDeleteWorkshop } from '../../hooks/useWorkshops';

interface WorkshopCardProps {
  workshop: Workshop;
}

export function WorkshopCard({ workshop }: WorkshopCardProps) {
  const deleteWorkshop = useDeleteWorkshop();

  const handleDelete = async () => {
    if (window.confirm(`Are you sure you want to delete workshop "${workshop.name}"?`)) {
      try {
        await deleteWorkshop.mutateAsync(workshop.name);
      } catch (error) {
        console.error('Failed to delete workshop:', error);
      }
    }
  };

  const getStatusColor = (phase?: string) => {
    switch (phase) {
      case 'Running':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'Pending':
      case 'Creating':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'Failed':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'Expired':
      case 'Expiring':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      default:
        return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  };

  // Extract data from the workshop spec for display
  const image = workshop.spec.image;
  const duration = workshop.spec.duration;
  const cpu = workshop.spec.resources.cpu;
  const memory = workshop.spec.resources.memory;
  const storage = workshop.spec.storage.size;

  return (
    <Card className="flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{workshop.name}</CardTitle>
          {workshop.status && (
            <Badge className={getStatusColor(workshop.status.phase)}>
              {workshop.status.phase}
            </Badge>
          )}
          {!workshop.status && (
            <Badge className="bg-gray-100 text-gray-800 border-gray-200">
              Unknown
            </Badge>
          )}
        </div>
        <CardDescription>
          Workshop in {workshop.namespace || 'default'} namespace
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-grow space-y-3">
        <div className="flex items-center text-sm text-muted-foreground">
          <Server className="h-4 w-4 mr-2" />
          <span>{image}</span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="font-medium">CPU:</span> {cpu}
          </div>
          <div>
            <span className="font-medium">Memory:</span> {memory}
          </div>
          <div>
            <span className="font-medium">Storage:</span> {storage}
          </div>
          <div>
            <span className="font-medium">Duration:</span> {formatDuration(duration)}
          </div>
        </div>

        {workshop.spec.participants && (
          <div className="text-sm">
            <span className="font-medium">Participants:</span> {workshop.spec.participants}
          </div>
        )}

        {workshop.created_at && (
          <div className="flex items-center text-sm text-muted-foreground">
            <Clock className="h-4 w-4 mr-2" />
            <span>Created {new Date(workshop.created_at).toLocaleString()}</span>
          </div>
        )}

        {workshop.status?.message && (
          <div className="text-sm text-muted-foreground bg-muted p-2 rounded">
            {workshop.status.message}
          </div>
        )}
      </CardContent>

      <CardFooter className="flex justify-between">
        <div className="flex space-x-2">
          <Link to={`/workshop/${workshop.name}`}>
            <Button variant="outline" size="sm">
              Details
            </Button>
          </Link>
          {workshop.connection_info?.url && workshop.status?.phase === 'Running' && (
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => window.open(workshop.connection_info?.url, '_blank')}
            >
              <ExternalLink className="h-4 w-4 mr-1" />
              Open
            </Button>
          )}
        </div>
        <Button
          variant="destructive"
          size="sm"
          onClick={handleDelete}
          disabled={deleteWorkshop.isPending}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  );
}
