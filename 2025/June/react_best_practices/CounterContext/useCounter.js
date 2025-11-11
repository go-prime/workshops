import { useContext } from 'react';
import { CounterStateContext, CounterDispatchContext } from './CounterContext';

export function useCounterState() {
  return useContext(CounterStateContext);
}

export function useCounterDispatch() {
  return useContext(CounterDispatchContext);
}
