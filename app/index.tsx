import { View, Text, StyleSheet, TouchableOpacity, Image } from 'react-native';
import { useRouter } from 'expo-router';

export default function Splash() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <Image source={require('../assets/images/sabaktutor-logo.png')} style={styles.logo} resizeMode="contain" />
        <Text style={styles.title}>
          <Text style={styles.titleGreen}>Moving Karachi{'\n'}from </Text>
          <Text style={styles.titleRed}>Ratta </Text>
          <Text style={styles.titleGreen}>to{'\n'}</Text>
          <Text style={styles.titleReason}>Reason.</Text>
        </Text>
        <Text style={styles.description}>
          Master STEM concepts with our{'\n'}Industrial-grade learning logic.
        </Text>
      </View>
      <View style={styles.buttonContainer}>
        <TouchableOpacity activeOpacity={0.7} style={styles.button} onPress={() => router.push('/signup')}>
          <Text style={styles.buttonText}>Let's Start 🚀</Text>
        </TouchableOpacity>
        
        <View style={styles.dividerContainer}>
          <View style={styles.dividerLine} />
          <Text style={styles.dividerText}>OR SIGN IN</Text>
          <View style={styles.dividerLine} />
        </View>

        <TouchableOpacity activeOpacity={0.7} style={[styles.button, styles.secondaryButton]} onPress={() => router.push('/login')}>
          <Text style={[styles.buttonText, styles.secondaryButtonText]}>I ALREADY HAVE AN ACCOUNT</Text>
        </TouchableOpacity>
      </View>
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
    alignItems: 'center',
  },
  logo: {
    width: 200,
    height: 200,
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: '800',
    textAlign: 'center',
    marginBottom: 24,
  },
  titleGreen: {
    color: '#156c40', // Dark green matching the image
  },
  titleRed: {
    color: '#b91c1c', // Deep red
  },
  titleReason: {
    color: '#16a34a', // Lighter green
  },
  description: {
    fontSize: 14,
    color: '#3d4a3e',
    textAlign: 'center',
    lineHeight: 22,
  },
  button: {
    backgroundColor: '#206b38', // Match the dark green button color
    paddingVertical: 16,
    borderRadius: 8,
    alignItems: 'center',
    borderBottomWidth: 4,
    borderBottomColor: '#104d23',
    marginBottom: 16,
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
  },
  buttonContainer: {
    marginBottom: 32,
  },
  dividerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 16,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: '#d1e4fb',
  },
  dividerText: {
    marginHorizontal: 12,
    color: '#004970',
    fontSize: 10,
    fontWeight: 'bold',
  },
  secondaryButton: {
    backgroundColor: '#f8fafc',
    borderBottomColor: '#d1e4fb',
    borderWidth: 2,
    borderColor: '#e2e8f0',
    borderBottomWidth: 4,
  },
  secondaryButtonText: {
    color: '#004970',
    fontSize: 12,
  },
});
