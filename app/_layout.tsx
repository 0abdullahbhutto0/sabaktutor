import { Stack, useRouter, useSegments } from 'expo-router';
import { useEffect, useState } from 'react';
import auth, { FirebaseAuthTypes } from '@react-native-firebase/auth';

export default function RootLayout() {
  const [initializing, setInitializing] = useState(true);
  const [user, setUser] = useState<FirebaseAuthTypes.User | null>(null);
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    const subscriber = auth().onAuthStateChanged((u) => {
      setUser(u);
      if (initializing) setInitializing(false);
    });
    return subscriber; 
  }, [initializing]);

  useEffect(() => {
    if (initializing) return;

    // Check if the current route is an authentication route (or the root page)
    const inAuthGroup = segments.length === 0 || segments[0] === 'login' || segments[0] === 'signup' || segments[0] === 'index' || segments[0] === '';

    if (user && inAuthGroup) {
      // If logged in and on an auth screen, send them into the app
      router.replace('/quiz-selection');
    } else if (!user && !inAuthGroup) {
      // If logged out and inside the app, kick them back to the welcome screen
      router.replace('/');
    }
  }, [user, initializing, segments]);

  if (initializing) return null;

  return (
    <Stack>
      <Stack.Screen name="index" options={{ headerShown: false, gestureEnabled: false }} />
      <Stack.Screen name="signup" options={{ headerTitle: 'Signup', headerBackTitle: 'Back' }} />
      <Stack.Screen name="login" options={{ headerTitle: 'Login', headerBackTitle: 'Back' }} />
      <Stack.Screen name="grade-selection" options={{ headerShown: false, gestureEnabled: false }} />
      <Stack.Screen name="subject-selection" options={{ headerShown: false, gestureEnabled: false }} />
      <Stack.Screen name="quiz-selection" options={{ headerShown: false, gestureEnabled: false }} />
      <Stack.Screen name="profile" options={{ headerShown: false, gestureEnabled: false, animation: 'fade' }} />
    </Stack>
  );
}
