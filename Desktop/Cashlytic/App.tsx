import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { AuthProvider } from './src/context/AuthContext'; // Assuming path: src/context/AuthContext.tsx
import { ExpenseProvider } from './src/context/ExpenseContext'; // Assuming path: src/context/ExpenseContext.tsx
// Assuming your RootNavigator is defined like this, adjust the import path if needed
import RootNavigator from './src/navigation/RootNavigator'; 
import { StatusBar } from 'expo-status-bar';

export default function App() {
  return (
    // AuthProvider provides user data (currently mock)
    <AuthProvider>
      {/* ExpenseProvider needs user from AuthProvider */}
      <ExpenseProvider>
        <NavigationContainer>
          {/* RootNavigator likely contains your Stack/Tab navigators */}
          <RootNavigator />
          <StatusBar style="auto" />
        </NavigationContainer>
      </ExpenseProvider>
    </AuthProvider>
  );
} 