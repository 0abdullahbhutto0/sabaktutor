import { Stack, useRouter, useSegments } from 'expo-router';
import { useEffect, useState } from 'react';
import { StatusBar } from 'expo-status-bar';
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
    const firstSegment = segments[0] as string | undefined;
    const inAuthGroup = firstSegment === 'login' || firstSegment === 'signup' || firstSegment === 'index' || firstSegment === '';

    if (user && inAuthGroup) {
      // If logged in and on an auth screen, send them into the app
      router.replace('/subject-selection');
    } else if (!user && !inAuthGroup) {
      // If logged out and inside the app, kick them back to the welcome screen
      router.replace('/');
    }
  }, [user, initializing, segments]);

  if (initializing) return null;

  return (
    <>
      <StatusBar style="dark" />
      <Stack>
        <Stack.Screen name="index" options={{ headerShown: false, gestureEnabled: false }} />
      <Stack.Screen name="signup" options={{ headerTitle: 'Signup', headerBackTitle: 'Back' }} />
      <Stack.Screen name="login" options={{ headerTitle: 'Login', headerBackTitle: 'Back' }} />
      <Stack.Screen name="grade-selection" options={{ headerShown: false, gestureEnabled: false }} />
      <Stack.Screen name="subject-selection" options={{ headerShown: false, gestureEnabled: false }} />
      <Stack.Screen name="(tabs)" options={{ headerShown: false, gestureEnabled: false }} />
      <Stack.Screen name="lesson/[id]" options={{ headerShown: false }} />
      <Stack.Screen name="quiz/[id]" options={{ headerShown: false }} />
      <Stack.Screen name="descriptive-quiz/[id]" options={{ headerShown: false }} />
      </Stack>
    </>
  );
}
