import { View, Text, TextInput, StyleSheet, TouchableOpacity, Alert, Image, KeyboardAvoidingView, Platform } from 'react-native';
import { useState } from 'react';
import auth from '@react-native-firebase/auth';
import firestore from '@react-native-firebase/firestore';
import { useRouter } from 'expo-router';
import ChunkyButton from './components/ChunkyButton';

export default function Signup() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [confirmEmail, setConfirmEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSignup = async () => {
    if (!username.trim() || !email.trim() || !password.trim()) {
      Alert.alert('Error', 'Please fill in all fields.');
      return;
    }
    
    if (email !== confirmEmail) {
      Alert.alert('Error', 'Emails do not match.');
      return;
    }

    try {
      const userCredential = await auth().createUserWithEmailAndPassword(email, password);
      await firestore().collection('users').doc(userCredential.user.uid).set({
        username,
        email,
        createdAt: firestore.FieldValue.serverTimestamp(),
      });
      router.replace('/grade-selection');
    } catch (error: any) {
      setError(error.message);
    }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.container}>
      <Image source={require('../assets/images/sabaktutor-logo.png')} style={styles.logo} resizeMode="contain" />
      <Text style={styles.header}>SabakTutor</Text>
      <Text style={styles.title}>Create your Profile</Text>
      <Text style={styles.subtitle}>Setup your logic-first identity</Text>
      
      <View style={styles.infoBox}>
        <Text style={styles.infoText}>🛡️ Privacy-first: We don't need your real name.</Text>
      </View>

      <TextInput
        style={styles.input}
        placeholder="Username"
        placeholderTextColor="#6c7b6d"
        autoCapitalize="none"
        value={username}
        onChangeText={setUsername}
      />
      <TextInput
        style={styles.input}
        placeholder="Email Address"
        placeholderTextColor="#6c7b6d"
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="Confirm Email Address"
        placeholderTextColor="#6c7b6d"
        autoCapitalize="none"
        keyboardType="email-address"
        value={confirmEmail}
        onChangeText={setConfirmEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        placeholderTextColor="#6c7b6d"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <ChunkyButton 
        title="Continue" 
        onPress={handleSignup} 
        style={{ marginTop: 16 }}
      />

      <Text style={styles.footer}>
        By continuing, you agree to our privacy guidelines. SabakTutor keeps your learning journey anonymous and safe.
      </Text>
      <TouchableOpacity activeOpacity={0.7} onPress={() => router.replace('/login')} style={styles.linkContainer}>
        <Text style={styles.linkText}>Already have an account? Login</Text>
      </TouchableOpacity>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f7f9ff',
    padding: 24,
    justifyContent: 'center',
  },
  logo: {
    width: 64,
    height: 64,
    marginBottom: 16,
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
    marginBottom: 24,
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
  },
  input: {
    backgroundColor: '#ffffff',
    borderWidth: 2,
    borderColor: '#bbcbbb',
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    marginBottom: 16,
    color: '#091d2e',
  },
  error: {
    color: '#b91c1c',
    marginBottom: 16,
    textAlign: 'center',
  },
  footer: {
    marginTop: 24,
    fontSize: 12,
    color: '#6c7b6d',
    textAlign: 'center',
  },
  linkContainer: {
    marginTop: 24,
    alignItems: 'center',
  },
  linkText: {
    color: '#006d37',
    fontSize: 16,
    fontWeight: '600',
  },
});
