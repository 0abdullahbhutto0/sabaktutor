import { Stack } from 'expo-router';

export default function RootLayout() {
  return (
    <Stack>
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen name="signup" options={{ headerTitle: 'Signup', headerBackTitle: 'Back' }} />
      <Stack.Screen name="login" options={{ headerTitle: 'Login', headerBackTitle: 'Back' }} />
      <Stack.Screen name="grade-selection" options={{ headerShown: false }} />
      <Stack.Screen name="subject-selection" options={{ headerShown: false }} />
      <Stack.Screen name="quiz-selection" options={{ headerTitle: 'Quizzes', headerBackTitle: 'Back', headerShown: false }} />
    </Stack>
  );
}
