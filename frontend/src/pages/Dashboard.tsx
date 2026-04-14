import React from 'react';
import { useWorkshops } from '../hooks/useWorkshops';
import { WorkshopCard } from '../components/workshop/WorkshopCard';
import { Button } from '../components/ui/Button';
import { Plus, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';

export function Dashboard() {
  const { data: workshopsData, isLoading, error, refetch } = useWorkshops();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span>Loading workshops...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <div className="text-center">
          <h2 className="text-lg font-semibold text-destructive">Failed to load workshops</h2>
          <p className="text-muted-foreground mt-2">
            {error instanceof Error ? error.message : 'Unknown error occurred'}
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            Make sure the API server is running at {import.meta.env.VITE_API_URL || 'http://localhost:8000'}
          </p>
        </div>
        <Button onClick={() => refetch()} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Try Again
        </Button>
      </div>
    );
  }

  const workshops = workshopsData?.items || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Workshop Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Manage your RStudio workshops
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={() => refetch()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Link to="/create">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Workshop
            </Button>
          </Link>
        </div>
      </div>

      {workshops.length === 0 ? (
        <div className="text-center py-12">
          <div className="mx-auto max-w-md">
            <h3 className="text-lg font-semibold">No workshops found</h3>
            <p className="text-muted-foreground mt-2">
              Get started by creating your first workshop
            </p>
            <Link to="/create">
              <Button className="mt-4">
                <Plus className="h-4 w-4 mr-2" />
                Create Your First Workshop
              </Button>
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {workshops.map((workshop) => (
            <WorkshopCard key={workshop.name} workshop={workshop} />
          ))}
        </div>
      )}

      <div className="text-sm text-muted-foreground">
        Total workshops: {workshops.length}
      </div>
    </div>
  );
}
