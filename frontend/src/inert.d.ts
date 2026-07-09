import 'react';

// React 18's type defs predate the `inert` attribute (first-class in React 19).
// Declare it so the off-canvas drawer can mark itself non-interactive when closed.
declare module 'react' {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars -- arity must match React's HTMLAttributes<T>
  interface HTMLAttributes<T> {
    inert?: '' | undefined;
  }
}
