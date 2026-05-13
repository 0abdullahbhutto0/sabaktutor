import { View, Text, TextInput, StyleSheet, Pressable, Alert } from 'react-native';
import { useState } from 'react';
import auth from '@react-native-firebase/auth';
import firestore from '@react-native-firebase/firestore';
import { useRouter } from 'expo-router';

export default function Signup() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [confirmEmail, setConfirmEmail] = useState('');
  const [password, setPassword] = useState('');
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
      Alert.alert('Error', error.message);
    }
  };

  return (
    <View style={styles.container}>
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

      <Pressable style={styles.button} onPress={handleSignup}>
        <Text style={styles.buttonText}>Continue</Text>
      </Pressable>

      <Text style={styles.footer}>
        By continuing, you agree to our privacy guidelines. SabakTutor keeps your learning journey anonymous and safe.
      </Text>
      <Pressable onPress={() => router.replace('/login')} style={styles.linkContainer}>
        <Text style={styles.linkText}>Already have an account? Login</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f7f9ff',
    padding: 24,
    justifyContent: 'center',
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
  button: {
    backgroundColor: '#006d37',
    paddingVertical: 16,
    borderRadius: 16,
    alignItems: 'center',
    borderBottomWidth: 4,
    borderBottomColor: '#005228',
    marginTop: 16,
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: '700',
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
