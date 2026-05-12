import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';

export default function Splash() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>SabakTutor</Text>
        <Text style={styles.subtitle}>Moving Karachi from Ratta to Reason.</Text>
        <Text style={styles.description}>
          Master STEM concepts with our industrial-grade learning logic.
          Powered by Agentic AI—No Videos, Just Logic.
        </Text>
      </View>
      <Pressable style={styles.button} onPress={() => router.push('/signup')}>
        <Text style={styles.buttonText}>Get Started</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f7f9ff',
    padding: 24,
    justifyContent: 'space-between',
  },
  content: {
    flex: 1,
    justifyContent: 'center',
  },
  title: {
    fontSize: 40,
    fontWeight: '700',
    color: '#006d37',
    marginBottom: 16,
  },
  subtitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#091d2e',
    marginBottom: 16,
  },
  description: {
    fontSize: 18,
    color: '#3d4a3e',
    lineHeight: 26,
  },
  button: {
    backgroundColor: '#006d37',
    paddingVertical: 16,
    borderRadius: 16,
    alignItems: 'center',
    borderBottomWidth: 4,
    borderBottomColor: '#005228',
    marginBottom: 32,
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: '700',
  },
});
