import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';

export default function QuizSelection() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <Text style={styles.header}>SabakTutor</Text>
      <Text style={styles.title}>Computer Science</Text>
      <Text style={styles.subtitle}>Select a Quiz</Text>
      
      <View style={styles.infoBox}>
        <Text style={styles.infoText}>More quizzes will be added here soon. Stay tuned!</Text>
      </View>

      <Pressable style={styles.backButton} onPress={() => router.back()}>
        <Text style={styles.backText}>Back to Subjects</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f7f9ff',
    padding: 24,
    paddingTop: 60,
  },
  header: {
    fontSize: 22,
    fontWeight: '600',
    color: '#006d37',
    marginBottom: 8,
  },
  title: {
    fontSize: 32,
    fontWeight: '700',
    color: '#091d2e',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 18,
    color: '#3d4a3e',
    marginBottom: 32,
  },
  infoBox: {
    backgroundColor: '#e3efff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 24,
  },
  infoText: {
    color: '#004970',
    fontWeight: '600',
    textAlign: 'center',
  },
  backButton: {
    marginTop: 'auto',
    paddingVertical: 16,
    alignItems: 'center',
  },
  backText: {
    color: '#006d37',
    fontSize: 16,
    fontWeight: '600',
  },
});
