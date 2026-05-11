import { AuthProvider } from './src/context/AuthContext';
import { VocalProfileProvider } from './src/context/VocalProfileContext';
import { GoalsProvider } from './src/context/GoalsContext';
import { FavoritesProvider } from './src/context/FavoritesContext';
import AppNavigator from './src/navigation/AppNavigator';

export default function App() {
  return (
    <AuthProvider>
      <VocalProfileProvider>
        <GoalsProvider>
          <FavoritesProvider>
            <AppNavigator />
          </FavoritesProvider>
        </GoalsProvider>
      </VocalProfileProvider>
    </AuthProvider>
  );
}
