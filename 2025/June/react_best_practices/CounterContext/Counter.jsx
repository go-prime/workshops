import React from 'react';
import { useCounterState, useCounterDispatch } from './CounterContext/useCounter';

function Counter() {
  const { count } = useCounterState();
  const dispatch = useCounterDispatch();

  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => dispatch({ type: 'decrement' })}>-</button>
      <button onClick={() => dispatch({ type: 'increment' })}>+</button>
      <button onClick={() => dispatch({ type: 'reset' })}>Reset</button>
    </div>
  );
}

export default Counter;
