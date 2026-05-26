/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState } from 'react';

interface PointsContextType {
  availablePoints: number;
  usePoints: (amount: number) => boolean;
  addPoints: (amount: number) => void;
  setPoints: (amount: number) => void;
  refreshPoints: () => void;
}

const PointsContext = createContext<PointsContextType | undefined>(undefined);

export const PointsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [availablePoints, setAvailablePoints] = useState<number>(() => {
    const storedPoints = localStorage.getItem('availablePoints');
    return storedPoints ? parseInt(storedPoints, 10) : 0;
  });

  const usePoints = (amount: number): boolean => {
    if (availablePoints < amount) {
      return false;
    }
    const newPoints = availablePoints - amount;
    setAvailablePoints(newPoints);
    localStorage.setItem('availablePoints', newPoints.toString());
    return true;
  };

  const addPoints = (amount: number) => {
    const newPoints = availablePoints + amount;
    setAvailablePoints(newPoints);
    localStorage.setItem('availablePoints', newPoints.toString());
  };

  const setPoints = (amount: number) => {
    setAvailablePoints(amount);
    localStorage.setItem('availablePoints', amount.toString());
  };

  const refreshPoints = () => {
    const storedPoints = localStorage.getItem('availablePoints');
    if (storedPoints) {
      setAvailablePoints(parseInt(storedPoints, 10));
    }
  };

  return (
    <PointsContext.Provider value={{ availablePoints, usePoints, addPoints, setPoints, refreshPoints }}>
      {children}
    </PointsContext.Provider>
  );
};

export const usePoints = () => {
  const context = useContext(PointsContext);
  if (!context) {
    throw new Error('usePoints must be used within a PointsProvider');
  }
  return context;
};
