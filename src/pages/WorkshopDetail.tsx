import React from 'react';
import { useParams } from 'react-router-dom';

export function WorkshopDetail() {
  const { name } = useParams<{ name: string }>();
  
  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Workshop: {name}</h1>
      <p className="text-muted-foreground">
        Workshop detail view will be available after installing dependencies.
      </p>
    </div>
  );
}
