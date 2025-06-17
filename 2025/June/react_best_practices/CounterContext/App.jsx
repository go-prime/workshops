import React from 'react';
import { CounterProvider } from './CounterContext/CounterProvider';
import Counter from './Counter';

function App() {
  return (
    <CounterProvider>
      <h1>Global Counter</h1>
      <Counter />
    </CounterProvider>
  );
}

export default App;
